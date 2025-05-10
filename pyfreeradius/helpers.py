from .repositories import GroupRepository, NasRepository, UserRepository
from .services import GroupService, NasService, UserService
from .settings import RadTables

#
# Helpers to get all repository and service instances.
#


class Repositories:
    def __init__(self, db_session, rad_tables: RadTables | None = None):
        self.user = UserRepository(db_session=db_session, rad_tables=rad_tables)
        self.group = GroupRepository(db_session=db_session, rad_tables=rad_tables)
        self.nas = NasRepository(db_session=db_session, rad_tables=rad_tables)


class Services:
    def __init__(self, db_session, rad_tables: RadTables | None = None):
        repositories = Repositories(db_session, rad_tables)
        self.user = UserService(user_repo=repositories.user, group_repo=repositories.group)
        self.group = GroupService(group_repo=repositories.group, user_repo=repositories.user)
        self.nas = NasService(nas_repo=repositories.nas)
