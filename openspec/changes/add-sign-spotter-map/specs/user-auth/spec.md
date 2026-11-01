# Spec Delta

## Purpose

Identifies users through GitHub sign-in so that only authenticated users (or trusted scripts with a dev API key) can add signs, while viewing stays public.

## ADDED Requirements

### Requirement: Sign in with GitHub
The system SHALL let a user sign in through GitHub OAuth. Visiting `/auth/login` SHALL redirect to GitHub's authorization page. A successful callback SHALL create a session identifying the user's GitHub login and redirect back to the app's home page.

#### Scenario: Successful sign-in
- **WHEN** a user visits `/auth/login` and approves the app on GitHub
- **THEN** the user is redirected back to `/` with an active session for their GitHub login

#### Scenario: Sign-in cancelled or failed
- **WHEN** the user denies access on GitHub, or the callback fails verification
- **THEN** the user is redirected to `/` with an error indication, and no session is created

### Requirement: Report the current user
The system SHALL expose `GET /auth/me`. It returns the signed-in user's GitHub login and avatar URL, or a null user when no one is signed in.

#### Scenario: Signed in
- **WHEN** a signed-in user calls `/auth/me`
- **THEN** the response contains their GitHub login and avatar URL

#### Scenario: Signed out
- **WHEN** an anonymous client calls `/auth/me`
- **THEN** the response contains a null user and status 200

### Requirement: Sign out
The system SHALL end the user's session when they visit `/auth/logout` and SHALL redirect them to `/`.

#### Scenario: Sign out
- **WHEN** a signed-in user visits `/auth/logout`
- **THEN** they are redirected to `/`, and `/auth/me` then reports a null user

### Requirement: Require authentication for uploads
Uploading a sign over REST or GraphQL SHALL require either an active GitHub session or a valid dev API key in the `X-API-Key` header. Unauthenticated uploads SHALL be rejected without storing anything. All read endpoints SHALL remain public.

#### Scenario: Anonymous upload rejected
- **WHEN** a client without a session or API key sends `POST /api/signs`
- **THEN** the response has status 401, and no sign or image is stored

#### Scenario: Anonymous GraphQL upload rejected
- **WHEN** a client without a session or API key calls the `uploadSign` mutation
- **THEN** the response contains an error with code `AUTH_REQUIRED`, and no sign is stored

#### Scenario: Wrong API key
- **WHEN** a client sends `POST /api/signs` with an incorrect `X-API-Key`
- **THEN** the response has status 401

#### Scenario: Reads stay public
- **WHEN** an anonymous client calls `GET /api/signs`
- **THEN** the response has status 200

### Requirement: Record the uploader
Each stored sign SHALL record who uploaded it: the GitHub login for session uploads, or `api-key` for API key uploads. It is returned as `uploadedBy`.

#### Scenario: Uploaded by a signed-in user
- **WHEN** GitHub user "octocat" uploads a sign through the UI
- **THEN** the returned and stored sign has `uploadedBy` "octocat"

#### Scenario: Uploaded by the seed script
- **WHEN** the seed command uploads a sample with the dev API key
- **THEN** the sign has `uploadedBy` "api-key"
