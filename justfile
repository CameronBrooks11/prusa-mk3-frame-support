default:
    @just --list

# Render the part and check its size, one solid, and that its slots and side holes are open
test:
    python3 tests/test_frame_support.py

# Render the README picture into assets/
images:
    @mkdir -p assets
    openscad --camera=40,103,11,45,0,30,480 --imgsize=800,560 --colorscheme=Tomorrow -o assets/frame-support.png frame_support.scad
