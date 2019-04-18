import os
import sys
import time
import random
import curses, curses.panel
import asyncio

from curses_tools import draw_frame, get_frame, get_frame_size, read_controls, get_colors
from physics import update_speed
from obstacles import Obstacle
from explosion import explode
from game_scenario import PHRASES, get_garbage_delay_tics


TIC_TIMEOUT = 0.1
TOTAL_STARS = 200
STARS_TYPES = '*.+o'

DELAY_DIM = int(2 / TIC_TIMEOUT)
DELAY_BOLD = int(0.5 / TIC_TIMEOUT)
DELAY_NORMAL = int(0.3 / TIC_TIMEOUT)

INTRO_FILE = 'frames/intro.txt'

SPACESHIP_STEP = 1
SPACESHIP_FILE = 'frames/spaceship_frame.txt'
SPACESHIP_FLAME_FILES = ['frames/spaceship_flame_frame_1.txt', 'frames/spaceship_flame_frame_2.txt']

GARBAGE_FRAMES_DIR = 'frames/garbage'
GARBAGE_SPEED = 0.1

YEAR_PLASMA_GUN_INVENTED = 2020
YEAR_START = 1957
YEARS_COUNT_SPEED = int(2 / TIC_TIMEOUT)

GAMEOVER_FILE = 'frames/gameover.txt'

coroutines = []
score = 0
colors = get_colors()

def intro(canvas):
    INTRO_FRAME = get_frame(INTRO_FILE)

    rows_number, columns_number = canvas.getmaxyx()
    height_intro, width_intro = get_frame_size(INTRO_FRAME)
    row_intro = rows_number / 2 - height_intro / 2
    column_intro = columns_number / 2 - width_intro / 2

    draw_frame(canvas, row_intro, column_intro, INTRO_FRAME)

def main(canvas):
    """Make some preparations, create coroutines and run event loop."""

    global coroutines, obstacles, obstacles_in_last_collisions, year


    #canvas.addstr(10,10,'!!!!!!!!!!!',curses.color_pair(1))

    obstacles = []
    obstacles_in_last_collisions = set()

    curses.curs_set(False)
    canvas.nodelay(True)

    row_max, column_max = canvas.getmaxyx()

    intro(canvas)

    # Create stars coordinates list and remove duplicates.
    coordinates = set([
        (random.randint(1, row_max-2), random.randint(1, column_max-2))
        for star in range(TOTAL_STARS)
    ])

    # Create coroutines list. Also add inside coroutines
    # fill_orbit_with_garbage() and
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
    coroutines.append(count_years())
    coroutines.append(show_win_info(canvas))
    coroutines.append(animate_spaceship_flame())
    coroutines.append(run_spaceship(canvas, int(row_max/1.5), column_max/2))
    coroutines.append(fill_orbit_with_garbage(canvas))

    # Run all coroutines in endless loop with interval TIC_TIMEOUT.
    while True:
        for coroutine in coroutines:
            try:
                coroutine.send(None)
                canvas.refresh()
            except StopIteration:
                coroutines.remove(coroutine)
        time.sleep(TIC_TIMEOUT)


async def show_win_info(canvas):
    """Show year and space epoch events on the left top corner. After 2020,
    when plasma gun will be invented, also show count of terminated pieces."""

    global year, score, colors

    win_info = canvas.derwin(10, 70, 1, 1)

    while True:
        if year in PHRASES:
            phrase = PHRASES[year]
        win_info.clrtoeol()
        win_info.addstr(0, 0, '{}: {}'.format(year, phrase), colors['green'])
        if year > YEAR_PLASMA_GUN_INVENTED:
            win_info.addstr(1, 0, '{} garbage objects terminated'.format(score), colors['green'])
        win_info.refresh()
        await asyncio.sleep(0)


async def count_years():
    global year
    year = YEAR_START
    while year <= YEAR_PLASMA_GUN_INVENTED:
        await sleep(YEARS_COUNT_SPEED)
        year += 1


async def fill_orbit_with_garbage(canvas):
    """Control space debris."""
    global coroutines, obstacles, year

    garbage_frames = []

    for filename in os.listdir(GARBAGE_FRAMES_DIR):
        with open(os.path.join(GARBAGE_FRAMES_DIR, filename), "r") as garbage_file:
            garbage_frames.append(garbage_file.read())

    rows_number, columns_number = canvas.getmaxyx()

    while True:
        # Create debris coroutines with random garbage type, random column and
        # delay depends on current year. Also create obstacles bounds.
        if get_garbage_delay_tics(year) is not None:
            column = random.randint(0, columns_number)
            garbage_frame = random.choice(garbage_frames)
            garbage_speed = random.randint(2, 10) * GARBAGE_SPEED
            coroutines.append(fly_garbage(canvas, column, garbage_frame, garbage_speed))
            #coroutines.append(show_obstacles(canvas, obstacles))
            await sleep(get_garbage_delay_tics(year))
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position
    will stay same, as specified on start."""

    global obstacles, obstacles_in_last_collisions, score

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    # Draw obstacle for collisions checks.
    obstacle_width, obstacle_height = get_frame_size(garbage_frame)
    obstacle = Obstacle(0, column, obstacle_width, obstacle_height)
    obstacles.append(obstacle)

    row = 0

    try:
        while row < rows_number:
            # Animate a garbage piece.
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            obstacle.row = row
            row += speed

            # Check for collision.
            if obstacle in obstacles_in_last_collisions:
                obstacles.remove(obstacle)
                await explode(canvas, row + obstacle_height / 2, column + obstacle_width / 2)
                score += 1
                obstacles_in_last_collisions.remove(obstacle)
                break
    finally:
        if obstacle in obstacles:
            obstacles.remove(obstacle)


async def run_spaceship(canvas, start_row, start_column):
    """Spaceship behavoir: control with arrow keys, animate frames,
    check for collisions with garbage."""

    global spaceship_frame, spaceship_flame_frame, coroutines, obstacles

    row = start_row
    column = start_column

    # Get canvas limits and spaceship dimentions.
    row_max, column_max = canvas.getmaxyx()
    spaceship_height,  spaceship_width = get_frame_size(spaceship_frame)
    row_limits = (0, row_max - spaceship_height)
    column_limits = (0, column_max - spaceship_width)

    row_speed = column_speed = 0
    previous_spaceship_flame_frame = ''
    previous_spaceship_frame = ''

    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        # Calculate new speed and new coordinates.
        row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)

        if row >= max(row_limits) and row_speed >= 0 or row <= min(row_limits) and row_speed <= 0:
            row_speed = 0
        row = row + row_speed

        if column >= max(column_limits) and column_speed >= 0 or column <= min(column_limits) and column_speed <= 0:
            column_speed = 0
        column = column + column_speed

        # Power-on the plasma gun.
        if space_pressed and year > YEAR_PLASMA_GUN_INVENTED:
            coroutines.append(animate_fire(canvas, row, column +2, rows_speed=-0.6, columns_speed=0))

        # Animate frames.
        draw_frame(canvas, row, column, spaceship_frame)
        draw_frame(canvas, row, column, spaceship_flame_frame, color='yellow')
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, previous_spaceship_frame, negative=True)
        draw_frame(canvas, row, column, previous_spaceship_flame_frame, negative=True)
        previous_spaceship_frame = spaceship_frame
        previous_spaceship_flame_frame = spaceship_flame_frame

        # Check for collisions with garbage.
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles.remove(obstacle)
                await explode(canvas, row, column)
                await show_gameover(canvas)
                return


async def animate_spaceship_flame():
    """Refresh spaceship frames."""

    global spaceship_frame, spaceship_flame_frame

    spaceship_frame = get_frame(SPACESHIP_FILE)

    while True:
        for filename in SPACESHIP_FLAME_FILES:
            spaceship_flame_frame = get_frame(filename)
            await asyncio.sleep(0)


async def animate_fire(canvas, start_row, start_column, rows_speed=-0.6, columns_speed=0):
    """Display shot animation. Direction and speed can be specified."""

    global obstacles_in_last_collisions

    row, column = start_row, start_column

    # Animate a shot.
    canvas.addstr(round(row), round(column), '*', colors['yellow'])
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), 'O', colors['yellow'])
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    # Animate a shot path.
    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol, colors['yellow'])
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed

        # Check fo collisions.
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.add(obstacle)
                return


async def animate_star(canvas, row, column, offset_ticks, symbol):
    """Draw blinking star."""

    while True:
        # delay before coroutine starting
        await sleep(offset_ticks)

        # Draw a star by coordinates and brightness.
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(DELAY_DIM)

        canvas.addstr(row, column, symbol)
        await sleep(DELAY_NORMAL)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(DELAY_BOLD)

        canvas.addstr(row, column, symbol)
        await sleep(DELAY_NORMAL)


async def sleep(delay):
    for _ in range(delay):
        await asyncio.sleep(0)


async def show_gameover(canvas):
    """Show Game Over if spaceship collision with garbage has been."""

    GAMEOVER_FRAME = get_frame(GAMEOVER_FILE)

    rows_number, columns_number = canvas.getmaxyx()
    height_gameover, width_gameover = get_frame_size(GAMEOVER_FRAME)
    row_gameover = rows_number / 2 - height_gameover / 2
    column_gameover = columns_number / 2 - width_gameover / 2

    while True:
        draw_frame(canvas, row_gameover, column_gameover, GAMEOVER_FRAME, color='red')
        await asyncio.sleep(0)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.initscr()
    curses.start_color()

    curses.wrapper(main)
