PHRASES = {
    1957: "First Sputnik",
    1958: "First solar powered satellite",
    1959: "First photograph of Earth from orbit",
    1960: "Belka and Strelka flew",
    1961: "Gagarin flew",
    1962: "First spacecraft to impact the far side of the Moon",
    1963: "Valentina Tereshkova in space",
    1964: "First multi-person crew",
    1965: "First space walk",
    1966: "Soft Moon landing",
    1967: "First docking of two spacecraft",
    1968: "First orbital ultraviolet observatory",
    1969: "Armstrong got on the Moon",
    1970: "Soft Venus landing",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "You got the plasma gun! Use the SPACE key!",
}

def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 50
    elif year < 1981:
        return 20
    elif year < 1995:
        return 15
    elif year < 2010:
        return 10
    elif year < 2020:
        return 6
    else:
        return 2
