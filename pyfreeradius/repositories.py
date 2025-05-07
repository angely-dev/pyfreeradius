from abc import ABC
from contextlib import closing

from .models import AttributeOpValue, Group, GroupUser, Nas, User, UserGroup
from .settings import RadTables

#
# As per the Repository pattern, repositories implement the mapping
# between the Domain Objects (the Pydantic models) and the database.
#
# The BaseRepository is the abstract superclass of the repositories.
#


class BaseRepository(ABC):
    def __init__(self, db_session, rad_tables: RadTables | None = None):
        self.db_session = db_session
        self.rad_tables = rad_tables or RadTables()


class UserRepository(BaseRepository):
    def exists(self, username: str) -> bool:
        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"""SELECT COUNT(DISTINCT username) FROM {self.rad_tables.radcheck} WHERE username = %s
                UNION SELECT COUNT(DISTINCT username) FROM {self.rad_tables.radreply} WHERE username = %s
                UNION SELECT COUNT(DISTINCT username) FROM {self.rad_tables.radusergroup} WHERE username = %s"""
            db_cursor.execute(sql, (username, username, username))
            counts = [count for (count,) in db_cursor.fetchall()]
            return sum(counts) > 0

    def find_one(self, username: str) -> User | None:
        if not self.exists(username):
            return None

        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"SELECT attribute, op, value FROM {self.rad_tables.radcheck} WHERE username = %s"
            db_cursor.execute(sql, (username,))
            checks = [AttributeOpValue(attribute=a, op=o, value=v) for a, o, v in db_cursor.fetchall()]

            sql = f"SELECT attribute, op, value FROM {self.rad_tables.radreply} WHERE username = %s"
            db_cursor.execute(sql, (username,))
            replies = [AttributeOpValue(attribute=a, op=o, value=v) for a, o, v in db_cursor.fetchall()]

            sql = f"SELECT groupname, priority FROM {self.rad_tables.radusergroup} WHERE username = %s"
            db_cursor.execute(sql, (username,))
            groups = [UserGroup(groupname=g, priority=p) for g, p in db_cursor.fetchall()]

            return User(username=username, checks=checks, replies=replies, groups=groups)

    def find(
        self, limit: int | None = 100, username_like: str | None = None, from_username: str | None = None
    ) -> list[User]:
        usernames = self.find_usernames(limit=limit, username_like=username_like, from_username=from_username)
        return [self.find_one(username) for username in usernames]  # type: ignore

    def find_usernames(
        self, limit: int | None = 100, username_like: str | None = None, from_username: str | None = None
    ) -> list[str]:
        where_clauses = []
        limit_clause = ""
        params: list[str | int] = []

        if username_like:
            where_clauses.append("username LIKE %s")
            params.append(username_like)

        if from_username:
            where_clauses.append("username >= %s")
            params.append(from_username)

        if limit:
            limit_clause = "LIMIT %s"
            params.append(limit)

        where_clauses_as_text = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT username FROM (
                    SELECT DISTINCT username FROM {self.rad_tables.radcheck}
              UNION SELECT DISTINCT username FROM {self.rad_tables.radreply}
              UNION SELECT DISTINCT username FROM {self.rad_tables.radusergroup}
            ) u {where_clauses_as_text} ORDER BY username {limit_clause}
        """

        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(sql, tuple(params)) if params else db_cursor.execute(sql)
            usernames = [username for (username,) in db_cursor.fetchall()]
            return usernames

    def add(self, user: User):
        with closing(self.db_session.cursor()) as db_cursor:
            for check in user.checks:
                sql = f"INSERT INTO {self.rad_tables.radcheck} (username, attribute, op, value) VALUES (%s, %s, %s, %s)"
                db_cursor.execute(sql, (user.username, check.attribute, check.op, check.value))

            for reply in user.replies:
                sql = f"INSERT INTO {self.rad_tables.radreply} (username, attribute, op, value) VALUES (%s, %s, %s, %s)"
                db_cursor.execute(sql, (user.username, reply.attribute, reply.op, reply.value))

            for group in user.groups:
                sql = f"INSERT INTO {self.rad_tables.radusergroup} (username, groupname, priority) VALUES (%s, %s, %s)"
                db_cursor.execute(sql, (user.username, group.groupname, group.priority))

    def set(
        self,
        username: str,
        new_checks: list[AttributeOpValue] | None = None,
        new_replies: list[AttributeOpValue] | None = None,
        new_groups: list[UserGroup] | None = None,
    ):
        with closing(self.db_session.cursor()) as db_cursor:
            if new_checks is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radcheck} WHERE username = %s", (username,))
                for check in new_checks:
                    sql = f"INSERT INTO {self.rad_tables.radcheck} (username, attribute, op, value) VALUES (%s, %s, %s, %s)"
                    db_cursor.execute(sql, (username, check.attribute, check.op, check.value))

            if new_replies is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radreply} WHERE username = %s", (username,))
                for reply in new_replies:
                    sql = f"INSERT INTO {self.rad_tables.radreply} (username, attribute, op, value) VALUES (%s, %s, %s, %s)"
                    db_cursor.execute(sql, (username, reply.attribute, reply.op, reply.value))

            if new_groups is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radusergroup} WHERE username = %s", (username,))
                for group in new_groups:
                    sql = f"INSERT INTO {self.rad_tables.radusergroup} (username, groupname, priority) VALUES (%s, %s, %s)"
                    db_cursor.execute(sql, (username, group.groupname, group.priority))

    def remove(self, username: str):
        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radcheck} WHERE username = %s", (username,))
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radreply} WHERE username = %s", (username,))
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radusergroup} WHERE username = %s", (username,))


class GroupRepository(BaseRepository):
    def exists(self, groupname: str) -> bool:
        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"""SELECT COUNT(DISTINCT groupname) FROM {self.rad_tables.radgroupcheck} WHERE groupname = %s
                UNION SELECT COUNT(DISTINCT groupname) FROM {self.rad_tables.radgroupreply} WHERE groupname = %s
                UNION SELECT COUNT(DISTINCT groupname) FROM {self.rad_tables.radusergroup} WHERE groupname = %s"""
            db_cursor.execute(sql, (groupname, groupname, groupname))
            counts = [count for (count,) in db_cursor.fetchall()]
            return sum(counts) > 0

    def find_one(self, groupname: str) -> Group | None:
        if not self.exists(groupname):
            return None

        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"SELECT attribute, op, value FROM {self.rad_tables.radgroupcheck} WHERE groupname = %s"
            db_cursor.execute(sql, (groupname,))
            checks = [AttributeOpValue(attribute=a, op=o, value=v) for a, o, v in db_cursor.fetchall()]

            sql = f"SELECT attribute, op, value FROM {self.rad_tables.radgroupreply} WHERE groupname = %s"
            db_cursor.execute(sql, (groupname,))
            replies = [AttributeOpValue(attribute=a, op=o, value=v) for a, o, v in db_cursor.fetchall()]

            sql = f"SELECT username, priority FROM {self.rad_tables.radusergroup} WHERE groupname = %s"
            db_cursor.execute(sql, (groupname,))
            users = [GroupUser(username=u, priority=p) for u, p in db_cursor.fetchall()]

            return Group(groupname=groupname, checks=checks, replies=replies, users=users)

    def find(
        self, limit: int | None = 100, groupname_like: str | None = None, from_groupname: str | None = None
    ) -> list[Group]:
        groupnames = self.find_groupnames(limit=limit, groupname_like=groupname_like, from_groupname=from_groupname)
        return [self.find_one(groupname) for groupname in groupnames]  # type: ignore

    def find_groupnames(
        self, limit: int | None = 100, groupname_like: str | None = None, from_groupname: str | None = None
    ) -> list[str]:
        where_clauses = []
        limit_clause = ""
        params: list[str | int] = []

        if groupname_like:
            where_clauses.append("groupname LIKE %s")
            params.append(groupname_like)

        if from_groupname:
            where_clauses.append("groupname >= %s")
            params.append(from_groupname)

        if limit:
            limit_clause = "LIMIT %s"
            params.append(limit)

        where_clauses_as_text = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT groupname FROM (
                    SELECT DISTINCT groupname FROM {self.rad_tables.radgroupcheck}
              UNION SELECT DISTINCT groupname FROM {self.rad_tables.radgroupreply}
              UNION SELECT DISTINCT groupname FROM {self.rad_tables.radusergroup}
            ) u {where_clauses_as_text} ORDER BY groupname {limit_clause}
        """

        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(sql, tuple(params)) if params else db_cursor.execute(sql)
            groupnames = [groupname for (groupname,) in db_cursor.fetchall()]
            return groupnames

    def has_users(self, groupname: str) -> bool:
        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"SELECT COUNT(DISTINCT username) FROM {self.rad_tables.radusergroup} WHERE groupname = %s"
            db_cursor.execute(sql, (groupname,))
            (count,) = db_cursor.fetchone()
            return count > 0

    def add(self, group: Group):
        with closing(self.db_session.cursor()) as db_cursor:
            for check in group.checks:
                sql = f"INSERT INTO {self.rad_tables.radgroupcheck} (groupname, attribute, op, value) VALUES (%s, %s, %s, %s)"
                db_cursor.execute(sql, (group.groupname, check.attribute, check.op, check.value))

            for reply in group.replies:
                sql = f"INSERT INTO {self.rad_tables.radgroupreply} (groupname, attribute, op, value) VALUES (%s, %s, %s, %s)"
                db_cursor.execute(sql, (group.groupname, reply.attribute, reply.op, reply.value))

            for user in group.users:
                sql = f"INSERT INTO {self.rad_tables.radusergroup} (groupname, username, priority) VALUES (%s, %s, %s)"
                db_cursor.execute(sql, (group.groupname, user.username, user.priority))

    def set(
        self,
        groupname: str,
        new_checks: list[AttributeOpValue] | None = None,
        new_replies: list[AttributeOpValue] | None = None,
        new_users: list[GroupUser] | None = None,
    ):
        with closing(self.db_session.cursor()) as db_cursor:
            if new_checks is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radgroupcheck} WHERE groupname = %s", (groupname,))
                for check in new_checks:
                    sql = f"INSERT INTO {self.rad_tables.radgroupcheck} (groupname, attribute, op, value) VALUES (%s, %s, %s, %s)"
                    db_cursor.execute(sql, (groupname, check.attribute, check.op, check.value))

            if new_replies is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radgroupreply} WHERE groupname = %s", (groupname,))
                for reply in new_replies:
                    sql = f"INSERT INTO {self.rad_tables.radgroupreply} (groupname, attribute, op, value) VALUES (%s, %s, %s, %s)"
                    db_cursor.execute(sql, (groupname, reply.attribute, reply.op, reply.value))

            if new_users is not None:
                db_cursor.execute(f"DELETE FROM {self.rad_tables.radusergroup} WHERE groupname = %s", (groupname,))
                for user in new_users:
                    sql = f"INSERT INTO {self.rad_tables.radusergroup} (groupname, username, priority) VALUES (%s, %s, %s)"
                    db_cursor.execute(sql, (groupname, user.username, user.priority))

    def remove(self, groupname: str):
        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radgroupcheck} WHERE groupname = %s", (groupname,))
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radgroupreply} WHERE groupname = %s", (groupname,))
            db_cursor.execute(f"DELETE FROM {self.rad_tables.radusergroup} WHERE groupname = %s", (groupname,))


class NasRepository(BaseRepository):
    def exists(self, nasname: str) -> bool:
        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"SELECT COUNT(DISTINCT nasname) FROM {self.rad_tables.nas} WHERE nasname = %s"
            db_cursor.execute(sql, (nasname,))
            (count,) = db_cursor.fetchone()
            return count > 0

    def find_one(self, nasname: str) -> Nas | None:
        if not self.exists(nasname):
            return None

        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"SELECT nasname, shortname, secret FROM {self.rad_tables.nas} WHERE nasname = %s"
            db_cursor.execute(sql, (nasname,))
            n, sh, se = db_cursor.fetchone()
            return Nas(nasname=n, shortname=sh, secret=se)

    def find(
        self, limit: int | None = 100, nasname_like: str | None = None, from_nasname: str | None = None
    ) -> list[Nas]:
        nasnames = self.find_nasnames(limit=limit, nasname_like=nasname_like, from_nasname=from_nasname)
        return [self.find_one(nasname) for nasname in nasnames]  # type: ignore

    def find_nasnames(
        self, limit: int | None = 100, nasname_like: str | None = None, from_nasname: str | None = None
    ) -> list[str]:
        where_clauses = []
        limit_clause = ""
        params: list[str | int] = []

        if nasname_like:
            where_clauses.append("nasname LIKE %s")
            params.append(nasname_like)

        if from_nasname:
            where_clauses.append("nasname >= %s")
            params.append(from_nasname)

        if limit:
            limit_clause = "LIMIT %s"
            params.append(limit)

        where_clauses_as_text = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT DISTINCT nasname FROM {self.rad_tables.nas}
            {where_clauses_as_text} ORDER BY nasname {limit_clause}
        """

        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(sql, tuple(params)) if params else db_cursor.execute(sql)
            nasnames = [nasname for (nasname,) in db_cursor.fetchall()]
            return nasnames

    def add(self, nas: Nas):
        with closing(self.db_session.cursor()) as db_cursor:
            sql = f"INSERT INTO {self.rad_tables.nas} (nasname, shortname, secret) VALUES (%s, %s, %s)"
            db_cursor.execute(sql, (nas.nasname, nas.shortname, nas.secret))

    def set(self, nasname: str, new_shortname: str | None = None, new_secret: str | None = None):
        with closing(self.db_session.cursor()) as db_cursor:
            if new_shortname is not None:
                sql = f"UPDATE {self.rad_tables.nas} SET shortname = %s WHERE nasname = %s"
                db_cursor.execute(sql, (new_shortname, nasname))

            if new_secret is not None:
                sql = f"UPDATE {self.rad_tables.nas} SET secret = %s WHERE nasname = %s"
                db_cursor.execute(sql, (new_secret, nasname))

    def remove(self, nasname: str):
        with closing(self.db_session.cursor()) as db_cursor:
            db_cursor.execute(f"DELETE FROM {self.rad_tables.nas} WHERE nasname = %s", (nasname,))
