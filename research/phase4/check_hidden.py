import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
import jev_decider as jd, mlx.core as mx
enc = jd.Encoder(str(ROOT / "research/phase4/models/Qwen2.5-0.5B-Instruct"))
cache = enc._mk(enc.model)
for c, p in zip(cache, enc.prefix): c.state = p.state
ids = mx.array(enc.tok.encode(jd.suffix("D2_action", "please deploy it"), add_special_tokens=False))[None]
old = enc.model.model(ids, cache=cache)[0, -1, :].astype(mx.float32)
new = enc.features_specs("D2_action", "please deploy it", ["final", "L12", "mean16-24", "L28"])
print("layers", enc.n_layers, "specs", list(new), "max|diff| final =", float(mx.abs(old - new["final"]).max().item()))
