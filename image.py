from pathlib import Path

__all__ = ["verify_progress"]


def verify_progress(before_path, after_path, threshold=0.08):
    """
    Verify visual progress between two images. Returns a dict with:
      - verdict: bool (True if progress detected, i.e., score >= threshold)
      - score: float (0..1 where higher means more difference)
      - threshold: float
      - detail: short message

    This attempts to use Pillow for a lightweight pixel-difference check; if Pillow
    is not available, it falls back to a file-size based heuristic so the app
    remains runnable without extra dependencies.
    """
    b = Path(before_path)
    a = Path(after_path)

    if not b.exists() or not a.exists():
        return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": "file missing"}

    try:
        from PIL import Image
    except Exception:
        # Fallback: use file size heuristic
        try:
            s1 = b.stat().st_size
            s2 = a.stat().st_size
            if max(s1, s2) == 0:
                score = 0.0
            else:
                score = abs(s2 - s1) / max(s1, s2)
            verdict = score >= threshold
            return {"verdict": verdict, "score": float(score), "threshold": threshold, "detail": "filesize-heuristic"}
        except Exception as e:
            return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": f"fallback-failed: {e}"}

    try:
        # Open, convert to grayscale and resize to speed up comparison
        im1 = Image.open(str(b)).convert("L").resize((64, 64), Image.LANCZOS)
        im2 = Image.open(str(a)).convert("L").resize((64, 64), Image.LANCZOS)

        p1 = list(im1.getdata())
        p2 = list(im2.getdata())

        # compute normalized mean absolute difference
        total_pixels = len(p1)
        if total_pixels == 0:
            return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": "empty-image"}

        diff = 0
        for x, y in zip(p1, p2):
            diff += abs(int(x) - int(y))

        # max possible diff per pixel is 255
        score = diff / (255.0 * total_pixels)
        verdict = score >= threshold
        return {"verdict": bool(verdict), "score": float(score), "threshold": threshold, "detail": "pillow-diff"}
    except Exception as e:
        return {"verdict": False, "score": 0.0, "threshold": threshold, "detail": f"error: {e}"}
