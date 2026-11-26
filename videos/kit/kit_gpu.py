"""Pick the best Blender compute device: OPTIX -> CUDA -> HIP -> METAL -> ONEAPI -> CPU. Run inside Blender.
Eevee always renders on the GPU through Blender's graphics backend; Cycles gets the compute device set here."""
import bpy


def setup(verbose=True):
    picked = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.refresh_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                picked = f"{kind} ({', '.join(d.name for d in devs)})"
                break
        for sc in bpy.data.scenes:
            if hasattr(sc, "cycles"):
                sc.cycles.device = "GPU" if picked != "CPU" else "CPU"
    except Exception as e:
        picked = f"CPU (device query failed: {e})"
    try:
        backend = bpy.context.preferences.system.gpu_backend
    except Exception:
        backend = "?"
    if verbose:
        print(f"[gpu] compute device: {picked}; Eevee graphics backend: {backend}", flush=True)
    return picked
