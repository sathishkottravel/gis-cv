# Spec Delta

## Purpose

Turns a single uploaded traffic sign photo into a recognized sign type with a confidence score, so it can be stored and shown on a map.

## ADDED Requirements

### Requirement: Classify an uploaded sign image
The system SHALL classify one uploaded image into exactly one traffic sign type from a fixed set of GTSRB classes (43 types). It SHALL return a human-readable label, a stable class identifier and a confidence between 0 and 1.

#### Scenario: Clear stop sign photo
- **WHEN** a user uploads a JPEG or PNG image showing a stop sign
- **THEN** the system returns the label "Stop", its class identifier and a confidence between 0 and 1

#### Scenario: Image of any size
- **WHEN** a user uploads a valid image of any resolution up to the size limit
- **THEN** the system classifies it without requiring the user to crop or resize it

### Requirement: Reject invalid uploads
The system SHALL reject uploads that are not decodable JPEG or PNG images, or that exceed 10 MB, with a clear error message, and it SHALL NOT store anything for them.

#### Scenario: Non-image file
- **WHEN** a user uploads a text file
- **THEN** the system returns an error saying the file is not a supported image, and no sign is stored

#### Scenario: Oversized file
- **WHEN** a user uploads an image larger than 10 MB
- **THEN** the system returns an error saying the file is too large, and no sign is stored

### Requirement: Flag low-confidence results
The system SHALL mark a classification as low confidence when its confidence is below 0.5. It SHALL still return and store that result.

#### Scenario: Ambiguous photo
- **WHEN** the top classification confidence is 0.32
- **THEN** the result is returned and stored with a low-confidence flag set to true
