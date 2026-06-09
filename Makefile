# Kenshi Diagrams — common flows

.PHONY: gen results gallery mono check train eval onnx clean

# Generate MellogangVisuals diagrams to out/
gen:
	python -m kenshi.cli --out out

# Generate result/with (model) and result/without (engine) for both projects
results:
	python scripts/generate_results.py

# Render PNG previews of every diagram into docs/img/
gallery:
	python scripts/make_gallery.py

# MellogangVisuals in monochrome (B/W) with transparent-background PNGs -> generated/
mono:
	python scripts/generate_mono.py

# Report overlap metrics (acceptance: 0 label + 0 shape overlaps)
check:
	python -m kenshi.cli --check

# Train the offline 'AI tidy' model (NOT committed; see .gitignore)
train:
	python ai/data_gen.py --n 12000 --out ai/artifacts/dataset.npz
	python ai/train.py  --data ai/artifacts/dataset.npz --out ai/artifacts/ringgnn.pt \
		--epochs 300 --batch 512 --hidden 96 --layers 4 --patience 25

eval:
	python ai/eval.py

onnx:
	python ai/export_onnx.py

clean:
	rm -rf out out_beauty preview_*.png ai/artifacts/*.npz ai/artifacts/*.pt \
		ai/artifacts/*.onnx ai/artifacts/test_idx.npy
