from enum import StrEnum

ALL = "ALL"


class PermissionName(StrEnum):
    TEAM_CREATE = "team:create"
    TEAM_ADD_USER = "team:add_user"
    TEAM_UPDATE = "team:update"
    TEAM_DELETE = "team:delete"

    PANEL_CREATE = "panel:create"
    PANEL_ADD_USER = "panel:add_user"
    PANEL_UPDATE = "panel:update"
    PANEL_DELETE = "panel:delete"

    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    DIRECTORY_CREATE = "directory:create"
    DIRECTORY_READ = "directory:read"
    DIRECTORY_UPLOAD = "directory:upload"
    DIRECTORY_APPROVE = "directory:approve"

    DOCUMENT_READ = "document:read"
    DOCUMENT_APPROVE = "document:approve"
    DOCUMENT_DELETE = "document:delete"


class ResourceType(StrEnum):
    ALL = ALL
    TEAM = "team"
    PANEL = "panel"
    DIRECTORY = "directory"
    DOCUMENT = "document"


_P, _R = PermissionName, ResourceType
_DIRECTORY_SCOPE = frozenset({_R.TEAM, _R.DIRECTORY})
_DOCUMENT_SCOPE = frozenset({_R.TEAM, _R.DIRECTORY, _R.DOCUMENT})

# Resource types a permission may be scoped to, besides "ALL" which every permission allows.
ALLOWED_RESOURCES: dict[PermissionName, frozenset[ResourceType]] = {
    _P.TEAM_CREATE: frozenset(),
    _P.TEAM_ADD_USER: frozenset(),
    _P.TEAM_UPDATE: frozenset({_R.TEAM}),
    _P.TEAM_DELETE: frozenset({_R.TEAM}),
    _P.PANEL_CREATE: frozenset(),
    _P.PANEL_ADD_USER: frozenset(),
    _P.PANEL_UPDATE: frozenset({_R.PANEL}),
    _P.PANEL_DELETE: frozenset({_R.PANEL}),
    _P.USER_CREATE: frozenset(),
    _P.USER_UPDATE: frozenset(),
    _P.USER_DELETE: frozenset(),
    _P.DIRECTORY_CREATE: frozenset({_R.TEAM}),
    _P.DIRECTORY_READ: _DIRECTORY_SCOPE,
    _P.DIRECTORY_UPLOAD: _DIRECTORY_SCOPE,
    _P.DIRECTORY_APPROVE: _DIRECTORY_SCOPE,
    _P.DOCUMENT_READ: _DOCUMENT_SCOPE,
    _P.DOCUMENT_APPROVE: _DOCUMENT_SCOPE,
    _P.DOCUMENT_DELETE: _DOCUMENT_SCOPE,
}
