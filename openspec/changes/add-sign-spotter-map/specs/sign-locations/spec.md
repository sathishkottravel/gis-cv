# Spec Delta

## Purpose

Stores recognized traffic signs as geographic points with their original image, exposes them through REST (with interactive docs) and GraphQL APIs, and provides sample sign images for testing.

## ADDED Requirements

### Requirement: Record a sign
The system SHALL accept a sign upload through both `POST /api/signs` (multipart form: `file`, optional `lat`, `lng`) and the GraphQL mutation `uploadSign` (base64 image, optional `lat`, `lng`). Both SHALL classify the image, store the sign as a WGS84 point and return the same fields: id, label, class identifier, confidence, low-confidence flag, latitude, longitude, location source, image URL, uploader and creation time.

#### Scenario: REST upload with explicit coordinates
- **WHEN** an authenticated client sends `POST /api/signs` with a valid image, `lat=48.137` and `lng=11.575`
- **THEN** the response has status 201 and contains a sign with a new id, the classification result, those coordinates and location source "manual"

#### Scenario: GraphQL upload with explicit coordinates
- **WHEN** an authenticated client calls `uploadSign` with a valid image, latitude 48.137 and longitude 11.575
- **THEN** the system returns a sign with the same fields and values as the REST upload would

### Requirement: Use photo GPS metadata when present
When the uploaded image contains EXIF GPS coordinates, the system SHALL use them as the sign location and report location source "exif". Coordinates in the EXIF data SHALL take precedence over coordinates passed in the request.

#### Scenario: Geotagged phone photo
- **WHEN** a client uploads an image whose EXIF data contains GPS latitude 52.52 and longitude 13.405, without passing coordinates
- **THEN** the stored sign is located at 52.52, 13.405 with location source "exif"

### Requirement: Require a location
The system SHALL reject an upload that has neither EXIF GPS data nor request coordinates, or whose coordinates fall outside latitude −90..90 or longitude −180..180. The error SHALL tell the client to choose a location, and nothing SHALL be stored.

#### Scenario: Photo without location
- **WHEN** a client uploads an image with no EXIF GPS data and no coordinates
- **THEN** the system returns a "location required" error (HTTP 422 over REST, error code `LOCATION_REQUIRED` over GraphQL), and no sign is stored

#### Scenario: Invalid coordinates
- **WHEN** a client uploads with latitude 120
- **THEN** the system returns a validation error, and no sign is stored

### Requirement: Keep the original image
The system SHALL store the original uploaded image in object storage and return, for every sign, an `imageUrl` that a browser can load without credentials. If the image cannot be stored, the upload SHALL fail with an error and no sign SHALL be recorded.

#### Scenario: Image retrievable after upload
- **WHEN** a client uploads a sign and then sends an HTTP GET request to the returned `imageUrl`
- **THEN** the response is the uploaded image with an image content type

#### Scenario: Storage unavailable
- **WHEN** the object storage service is down and a client uploads a sign
- **THEN** the system returns an "image storage unavailable" error (HTTP 503 over REST), and no sign is stored

### Requirement: Query signs by bounding box
The system SHALL return signs through `GET /api/signs` and the GraphQL `signs` query. Both take an optional bounding box (min/max longitude and latitude) and return only the signs whose location falls inside it, or all signs when no box is given, newest first, capped at 500 results. Reading signs SHALL NOT require authentication.

#### Scenario: Signs in the visible map area
- **WHEN** an anonymous client requests signs with a bounding box covering central Munich, and there are 3 signs inside it and 2 outside it
- **THEN** the response contains exactly the 3 signs inside the box

### Requirement: Filter signs by type
The sign queries SHALL accept an optional sign class identifier and, when one is given, return only signs of that class. This filter combines with the bounding box.

#### Scenario: Only stop signs
- **WHEN** a client queries signs with the stop sign class identifier
- **THEN** every returned sign has the label "Stop"

### Requirement: List sign types
The system SHALL return every supported class identifier with its label through `GET /api/sign-types` and the GraphQL `signTypes` query, so clients can build filters.

#### Scenario: Populate a filter dropdown
- **WHEN** a client requests the sign types
- **THEN** the response lists 43 entries, each with a class identifier and a label

### Requirement: Interactive REST API documentation
The system SHALL serve interactive OpenAPI (Swagger) documentation at `/docs` that describes every REST endpoint with its parameters and response shapes, and lets a user try the upload endpoint after entering an API key.

#### Scenario: Try an upload from Swagger
- **WHEN** a developer opens `/docs`, authorizes with the dev API key and runs `POST /api/signs` with a sample image and coordinates
- **THEN** the request succeeds and Swagger shows the returned sign JSON

#### Scenario: Endpoints listed
- **WHEN** a developer opens `/docs`
- **THEN** `POST /api/signs`, `GET /api/signs`, `GET /api/sign-types` and `GET /api/samples` are all listed

### Requirement: Register sample images in object storage
The project SHALL provide a command that downloads the public GTSRB test set and registers at least 20 PNG sign images, each of a different class, in a `samples` object storage bucket, together with a `manifest.json` object listing each file's expected class identifier and label.

#### Scenario: Fetch and register samples
- **WHEN** a developer runs the sample command on a machine with network access and the storage service running
- **THEN** the `samples` bucket contains at least 20 PNG objects and a `manifest.json` naming each one's expected class

### Requirement: List sample images
The system SHALL return the registered samples through `GET /api/samples`, each with its file name, expected class identifier, label and a URL a browser can download without credentials.

#### Scenario: Browse samples
- **WHEN** a client calls `GET /api/samples` after samples are registered
- **THEN** the response lists every manifest entry, and each URL returns the PNG image

### Requirement: Seed sample signs
The project SHALL provide a seed command that reads the sample manifest from object storage and uploads every sample through `POST /api/signs` using the dev API key, each at a distinct preset coordinate inside one city area.

#### Scenario: Seed an empty database
- **WHEN** a developer runs the seed command against an empty database with the API running
- **THEN** `GET /api/signs` returns one sign per sample, each with an `imageUrl` and a distinct location
