import sys
import time
import asyncio
import curses
import random

TIC_TIMEOUT = 0.1
TOTAL_STARS = 200
STARS_TYPES = '*.+o'

DELAY_DIM = 20
DELAY_BOLD = 5
DELAY_NORMAL = 3

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258

STEP_SPACESHIP = 1


def main(canvas):
    """Make some preparations, create coroutines and run event loop."""

    curses.curs_set(False)
    canvas.nodelay(True)

    rocket_frames = [
        get_frame('frames/rocket_frame_1.txt'),
        get_frame('frames/rocket_frame_2.txt')
    ]
    row_max, column_max = canvas.getmaxyx()

    # Create stars coordinates list and remove duplicates.
    coordinates = set([
        (random.randint(1, row_max-2), random.randint(1, column_max-2))
        for star in range(TOTAL_STARS)
    ])

    # Create coroutines list.
    coroutines = [
        animate_star(
            canvas,
            row,
            column,
            offset_ticks=random.randint(0, DELAY_DIM),
            symbol=random.choice(STARS_TYPES)
        )
        for row, column in coordinates
    ]
    coroutines.append(animate_spaceship(canvas, row_max/2, column_max/2, rocket_frames))
    coroutines.append(animate_fire(canvas, row_max/2, column_max/2, rows_speed=-0.6, columns_speed=0))

    # Run all coroutines in endless loop with interval.
    while True:
        for coroutine in coroutines:
            try:
                coroutine.send(None)
                canvas.refresh()
            except StopIteration:
                coroutines.remove(coroutine)
        time.sleep(TIC_TIMEOUT)


async def animate_star(canvas, row, column, offset_ticks, symbol):
    """Draw blinking star."""

    while True:
        # delay before coroutine starting
        for _ in range(offset_ticks):
            await asyncio.sleep(0)

        # Draw a star by coordinates and brightness.
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(DELAY_DIM):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(DELAY_NORMAL):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(DELAY_BOLD):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(DELAY_NORMAL):
            await asyncio.sleep(0)


async def animate_fire(canvas, start_row, start_column, rows_speed=-0.6, columns_speed=0):
    """Display shot animation. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def get_coordinate(direction, coordinate, limits):
    """Get new spaceship coordinate inside canvas limits."""

    limit_min, limit_max = limits
    if coordinate >= limit_max:
        if direction < 0:
            coordinate += direction
    elif coordinate <= limit_min:
        if direction > 0:
            coordinate += direction
    else:
        coordinate += direction
    return coordinate


async def animate_spaceship(canvas, start_row, start_column, frames):
    """Animate spaceship and get user control with arrow keys."""

    frame1, frame2 = frames
    row = start_row
    column = start_column

    # Get canvas limits.
    row_max, column_max = canvas.getmaxyx()
    spaceship_height,  spaceship_width = get_frame_size(frame1)
    row_limits = (0, row_max - spaceship_height)
    column_limits = (0, column_max - spaceship_width)

    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        # Get new coordinates.
        row = get_coordinate(rows_direction, row, row_limits)
        column = get_coordinate(columns_direction, column, column_limits)

        # Draw animation.
        draw_frame(canvas, row, column, frame2, negative=False)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame2, negative=True)
        draw_frame(canvas, row, column, frame1, negative=False)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame1, negative=True)


def get_frame(path):
    """Get frame for animation from text file."""
    with open(path) as file:
        return file.read()


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -STEP_SPACESHIP

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = STEP_SPACESHIP

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = STEP_SPACESHIP

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -STEP_SPACESHIP

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas.
    Erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            # Check that current position it is not in a lower right corner of
            # the window. Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_frame_size(text):
    """Calculate size of multiline text fragment."""
    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)
