<div align="center">

<img src="docs/images/hero.svg" alt="spacegraph: spatial memory for AI agents. A bedroom floor plan seen by four cameras at once." width="100%">

**Your agents can write a beautiful scene. spacegraph makes sure it's the same room every time.**

[Get started](docs/REFERENCE.md) · MIT licensed

</div>

## The problem

Ask an agent for twelve shots of the same bedroom and you get twelve bedrooms.

<img src="docs/images/drift.svg" alt="Left: twelve small floor plans, each with the bed, window and nightstand in a different place. Right: one floor plan with four cameras all looking into the same room." width="100%">

## The fix

Describe the space once. Then any agent can point a camera and ask: **"What do I actually see from here?"**

<img src="docs/images/view.svg" alt="Floor plan of the example bedroom with a camera at the doorway. Objects in its view cone are highlighted; beside it, the spacegraph report lists what is in frame, partly in frame and out of frame." width="100%">

<img src="docs/images/features.svg" alt="Four feature cards: relations not coordinates, plain language or JSON, drift check before the render, no impossible spaces or shots." width="100%">

<img src="docs/images/mirror.svg" alt="Top-down diagram: a camera, a woman facing a mirror, and their reflections on the far side of the glass, with the camera's own reflection flagged." width="100%">

Indoors or outdoors: bedrooms, streets, beaches. No engine, no GPU, no dependencies.

## Built for multi-agent pipelines

<img src="docs/images/pipeline.svg" alt="Three stages: a director agent writes the world once, scene agents each view it from their own camera, and a review pass checks finished prompts and flags drift." width="100%">

## Try it

```bash
pip install git+https://github.com/evolite/spacegraph

spacegraph view  examples/bedroom.json --shot doorway_wide
spacegraph map   examples/bedroom.json --shot doorway_wide
spacegraph check examples/bedroom.json --shot doorway_wide --text @prompt.txt
```

Python 3.10+. Full reference: [docs/REFERENCE.md](docs/REFERENCE.md).

<div align="center"><sub>Diagrams drawn from <code>examples/bedroom.json</code> by <code>docs/images/generate.py</code>.</sub></div>
