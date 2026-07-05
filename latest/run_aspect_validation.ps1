$regenDir = "C:\Users\mohdw\OneDrive\Desktop\geo\Latest\runs\roundtrip_annulus_demo\regenerated_prms"

wsl docker run --rm -v "/mnt/c/Users/mohdw/OneDrive/Desktop/geo/Latest/runs/roundtrip_annulus_demo/regenerated_prms:/workspace" geodynamics/aspect:latest bash -lc "cd /workspace && ls && for f in *.prm; do echo '=== '\"\$f\"' ==='; aspect \"\$f\"; done"
