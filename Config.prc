# Window / engine configuration for Cube Character in a 3D World.
# Loaded by main.py before ShowBase starts (the title is also set from main.py so
# all window tuning lives in one place).

window-title Cube Character in a 3D World
win-size 1280 720

# Smooth edges on the solid-coloured procedural geometry.
framebuffer-multisample 1
multisamples 4

# No audio is used; load the null audio library so no device is opened.
audio-library-name null
