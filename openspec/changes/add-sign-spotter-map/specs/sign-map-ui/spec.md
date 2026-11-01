# Spec Delta

## Purpose

Gives users one browser page where they can sign in with GitHub, upload a traffic sign photo, see what it was recognized as, and browse all recorded signs on a map.

## ADDED Requirements

### Requirement: Sign in and out from the page
The page SHALL show a "Sign in with GitHub" control when no one is signed in. When a user is signed in, it SHALL show their GitHub login, their avatar and a "Sign out" control. The map SHALL be viewable either way.

#### Scenario: Anonymous visitor
- **WHEN** a signed-out user opens the page
- **THEN** the map with markers and a "Sign in with GitHub" control are shown, and the upload form is not

#### Scenario: Signed-in visitor
- **WHEN** a signed-in user opens the page
- **THEN** their GitHub login, avatar, a "Sign out" control and the upload form are shown

#### Scenario: Sign-in failed
- **WHEN** the page loads after a failed or cancelled GitHub sign-in
- **THEN** a readable "sign-in failed" message is shown

### Requirement: Show stored signs on a map
The page SHALL display an interactive map with a marker for each stored sign in the visible area, and SHALL reload the markers when the user pans or zooms.

#### Scenario: Open the page
- **WHEN** a user opens the page and signs exist in the initial map view
- **THEN** a marker appears at each sign's location

#### Scenario: Pan to a new area
- **WHEN** the user pans the map to an area that contains other signs
- **THEN** markers for those signs appear without a full page reload

### Requirement: Show sign details on a marker
Clicking a marker SHALL show a thumbnail of the sign's stored image, its label, confidence as a percentage, a low-confidence warning when it applies, who uploaded it, and the time it was recorded.

#### Scenario: Inspect a marker
- **WHEN** the user clicks the marker of a stop sign that "octocat" recorded with confidence 0.94
- **THEN** a popup shows the image thumbnail, "Stop", "94%", "octocat" and the recording time

### Requirement: Upload a sign photo from the page
For signed-in users, the page SHALL provide a file picker for uploading an image. After a successful upload it SHALL show the recognized label and confidence, add the new marker and center the map on it.

#### Scenario: Upload a geotagged photo
- **WHEN** the user selects a geotagged sign photo and submits it
- **THEN** the page shows the recognized label and confidence, and a new marker appears at the photo's location

### Requirement: Pick a location when the photo has none
The page SHALL let the user click the map to set a location for the upload. If the server reports that a location is missing, the page SHALL prompt the user to click the map and then resubmit.

#### Scenario: Photo without GPS
- **WHEN** the user uploads a photo without GPS data and has not clicked the map
- **THEN** the page shows a message asking the user to click the map to choose the location

#### Scenario: Location chosen by click
- **WHEN** the user clicks a point on the map and then uploads a photo without GPS data
- **THEN** the sign is stored at the clicked point and its marker appears there

### Requirement: Filter markers by sign type
The page SHALL provide a sign-type filter, populated from the supported sign types, that limits the visible markers to the selected type, with an "All" option.

#### Scenario: Filter to yield signs
- **WHEN** the user selects "Yield" in the filter
- **THEN** only yield sign markers remain on the map

### Requirement: Show errors to the user
The page SHALL display server errors, such as an invalid file, a missing location or an expired session, as readable messages and SHALL NOT fail silently.

#### Scenario: Unsupported file
- **WHEN** the user uploads a PDF
- **THEN** the page shows the server's "not a supported image" message
