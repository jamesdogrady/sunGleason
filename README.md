# sunGleason
Sunlight visualization on purported flat earth map.
python script that shows daylight on a "Gleason" map, which is a AzimuthalEquidistant projection of the globe centered on the north pole.  Becasue one can travel east or west without going off the ends of the earth, this is purported to be a map of a flat earth.  The visualiztion uses the astral library to see if it's day or night at a given time and shades the map to show this.  Spoiler alert:  the light behaves inconsistently over the course of a year, indication that this map is not correct.  

Astral assumes a globe earth in it's calculations, but there are either right or wrong no matter how they are derived.  They calculations match observations (of course).

Note if you center the map over point on the globe where it's solar noon, you get a circle of daylight as you expect.  if you center the point on the antipode, you'll see a circle of darkness.  
