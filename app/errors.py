"""Domain errors raised by the service layer and mapped by REST/GraphQL."""


class DomainError(Exception):
    code = "DOMAIN_ERROR"


class InvalidImage(DomainError):
    code = "INVALID_IMAGE"


class LocationRequired(DomainError):
    code = "LOCATION_REQUIRED"


class InvalidCoordinates(DomainError):
    code = "INVALID_COORDINATES"


class StorageUnavailable(DomainError):
    code = "STORAGE_UNAVAILABLE"


class AuthRequired(DomainError):
    code = "AUTH_REQUIRED"
