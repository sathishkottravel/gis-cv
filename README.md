# Sign Spotter Map (gis-cv)

A small computer-vision + GIS demo: sign in with GitHub, upload a traffic sign photo, have it classified by a pretrained GTSRB model, and see it as a pin on a map.

**Stack:** FastAPI (REST + Swagger) · Strawberry GraphQL · PostGIS · MinIO · Hugging Face / PyTorch · Leaflet · GitHub OAuth

## Status

Planning stage. The full plan lives in [`openspec/changes/add-sign-spotter-map/`](openspec/changes/add-sign-spotter-map/):

- [`proposal.md`](openspec/changes/add-sign-spotter-map/proposal.md): why and what
- [`design.md`](openspec/changes/add-sign-spotter-map/design.md): how
- [`specs/`](openspec/changes/add-sign-spotter-map/specs/): behavior requirements
- [`tasks.md`](openspec/changes/add-sign-spotter-map/tasks.md): implementation checklist

Setup and usage instructions will be added here as the implementation lands.

## Contributing

All changes reach `main` through pull requests.
