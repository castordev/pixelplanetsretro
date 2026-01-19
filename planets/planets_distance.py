from skyfield.api import load, Topos    #topos crea un punto en la tierra con lat y lon
import datetime                         #load carga las efemérides


ts = load.timescale()           #convertimos la fecha y hora a un formato que skyfield entienda
bodies = load("de440.bsp")      #cargamos las efemérides

#latitud y longitud de vigo
lat = 42.2406
lon = -8.7207


#seleccionamos el planeta tierra y luego le decimos nuestra posición
earth = bodies["earth"]
location = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)


#alias para no tener que poner barycenter, etc.
aliases = {
    "mercury":  "mercury",
    "venus":    "venus",
    "earth":    "earth",
    "mars":     "mars barycenter",
    "jupiter":  "jupiter barycenter",
    "saturn":   "saturn barycenter",
    "uranus":   "uranus barycenter",
    "neptune":  "neptune barycenter",
    "pluto":    "pluto barycenter"
}


#funcion que recibe el nombre que skyfield necesita para devolver la distancia                                                        
def distance_body(name):        

    if name == "earth":  #comprobamos si es la tierra lo que piden
        return 0
    
    body = bodies[name]
    astrom = location.at(ts.now()).observe(body)
    return astrom.distance().km


#funcion que recibe el nombre que el usuario introduce y lo traduce para skyfield
def get_distance(planet_input):
    planet_name = aliases[planet_input.lower().strip()]
    return distance_body(planet_name)