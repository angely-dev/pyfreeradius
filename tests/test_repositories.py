from mysql.connector import connect
from pydantic import ValidationError
from pyfreeradius import Repositories
from pyfreeradius.models import AttributeOpValue, Group, GroupUser, Nas, User, UserGroup
from pytest import fixture, raises

#
# Each test will depend on repositories instance.
#


@fixture
def repositories():
    db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
    try:
        yield Repositories(db_session)
    except:
        # on any error, we rollback the DB
        db_session.rollback()
        raise
    else:
        # otherwise, we commit the DB
        db_session.commit()
    finally:
        # in any case, we close the DB session
        db_session.close()


#
# Some data reused across the tests.
#

checks = [AttributeOpValue(attribute="a", op=":=", value="b")]
replies = [AttributeOpValue(attribute="c", op=":=", value="d")]

#
# The tests.
#


def test_invalid_user():
    with raises(ValidationError):
        # Field username is required
        User()
    with raises(ValidationError):
        # User must have at least one check or one reply attribute
        #   or must have at least one group
        User(username="usr")
    with raises(ValidationError):
        # Given groups have one or more duplicates
        User(
            username="usr",
            checks=checks,
            replies=replies,
            groups=[UserGroup(groupname="not-unique"), UserGroup(groupname="not-unique")],
        )


def test_invalid_group():
    with raises(ValidationError):
        # Field groupname is required
        Group()
    with raises(ValidationError):
        # Group must have at least one check or one reply attribute
        #    or must have at least one user
        Group(groupname="grp")
    with raises(ValidationError):
        # Given users have one or more duplicates
        Group(
            groupname="grp",
            checks=checks,
            replies=replies,
            users=[GroupUser(username="not-unique"), GroupUser(username="not-unique")],
        )


def test_invalid_usergroup():
    with raises(ValidationError):
        # Field groupname is required
        UserGroup()
    with raises(ValidationError):
        # Field username is required
        GroupUser()


def test_invalid_nas():
    with raises(ValidationError):
        # Fields nasname, shortname, secret are required
        Nas()


def test_user_belongs_to_group():
    user = User(username="usr", groups=[UserGroup(groupname="grp1"), UserGroup(groupname="grp2")])
    assert user.belongs_to_group(groupname="grp1")
    assert user.belongs_to_group(groupname="grp2")
    assert not user.belongs_to_group(groupname="grp3")


def test_group_contains_user():
    group = Group(groupname="grp", users=[GroupUser(username="usr1"), GroupUser(username="usr2")])
    assert group.contains_user(username="usr1")
    assert group.contains_user(username="usr2")
    assert not group.contains_user(username="usr3")


def test_valid_user(repositories):
    user = User(username="usr", checks=checks, replies=replies)

    # adding
    assert not repositories.user.exists(user.username)
    repositories.user.add(user)
    assert repositories.user.exists(user.username)
    assert repositories.user.find_one(user.username) == user

    # modifying
    repositories.user.set(user.username, new_replies=checks, new_checks=replies)
    assert repositories.user.find_one(user.username).replies == checks
    assert repositories.user.find_one(user.username).checks == replies

    # removing
    repositories.user.remove(user.username)
    assert not repositories.user.exists(user.username)
    assert repositories.user.find_one(user.username) is None

    # find
    users = []
    for i in range(200):
        user = User(username=f"usr{i}", checks=checks, replies=replies)
        users.append(user)
        repositories.user.add(user)

    assert len(repositories.user.find()) == 100  # limits defaults to 100
    assert len(repositories.user.find(limit=20)) == 20
    assert len(repositories.user.find(limit=None)) == 200  # all results

    assert repositories.user.find(username_like="usr5%") == [users[5]] + users[50:60]  # usr5, usr50-59
    assert repositories.user.find(username_gt="usr9") == users[90:100]  # usr90-99
    assert repositories.user.find(username_like="usr5%", username_gt="usr55") == users[56:60]  # usr56-59

    assert repositories.user.find(limit=5, username_like="usr5%") == [users[5]] + users[50:54]  # usr5, u50-53
    assert repositories.user.find(limit=5, username_gt="usr9") == users[90:95]  # u90-94

    assert repositories.user.find(limit=5, username_gt="usr55", username_like="usr5%") == users[56:60]  # usr56-59

    for user in users:
        repositories.user.remove(user.username)


def test_valid_group(repositories):
    group = Group(groupname="grp", checks=checks, replies=replies)

    # adding
    assert not repositories.group.exists(group.groupname)
    repositories.group.add(group)
    assert repositories.group.exists(group.groupname)
    assert repositories.group.find_one(group.groupname) == group

    # modifying
    repositories.group.set(group.groupname, new_replies=checks, new_checks=replies)
    assert repositories.group.find_one(group.groupname).replies == checks
    assert repositories.group.find_one(group.groupname).checks == replies

    # removing
    repositories.group.remove(group.groupname)
    assert not repositories.group.exists(group.groupname)
    assert repositories.group.find_one(group.groupname) is None

    # find
    groups = []
    for i in range(200):
        group = Group(groupname=f"grp{i}", checks=checks, replies=replies)
        groups.append(group)
        repositories.group.remove(group.groupname)
        repositories.group.add(group)

    assert len(repositories.group.find()) == 100  # limits defaults to 100
    assert len(repositories.group.find(limit=20)) == 20
    assert len(repositories.group.find(limit=None)) == 200  # all results

    assert repositories.group.find(groupname_like="grp5%") == [groups[5]] + groups[50:60]  # grp5, grp50-59
    assert repositories.group.find(groupname_gt="grp9") == groups[90:100]  # grp90-99
    assert repositories.group.find(groupname_like="grp5%", groupname_gt="grp55") == groups[56:60]  # grp56-59

    assert repositories.group.find(limit=5, groupname_like="grp5%") == [groups[5]] + groups[50:54]  # grp5, grp50-53
    assert repositories.group.find(limit=5, groupname_gt="grp9") == groups[90:95]  # grp90-94

    assert repositories.group.find(limit=5, groupname_gt="grp55", groupname_like="grp5%") == groups[56:60]  # grp56-59

    for group in groups:
        repositories.group.remove(group.groupname)


def test_valid_nas(repositories):
    nas = Nas(nasname="nas", shortname="sh", secret="se")

    # adding
    assert not repositories.nas.exists(nas.nasname)
    repositories.nas.add(nas)
    assert repositories.nas.exists(nas.nasname)
    assert repositories.nas.find_one(nas.nasname) == nas

    # modifying
    repositories.nas.set(nas.nasname, new_shortname="new-sh", new_secret="new-se")
    assert repositories.nas.find_one(nas.nasname).shortname == "new-sh"
    assert repositories.nas.find_one(nas.nasname).secret == "new-se"

    # removing
    repositories.nas.remove(nas.nasname)
    assert not repositories.nas.exists(nas.nasname)
    assert repositories.nas.find_one(nas.nasname) is None

    # find
    nases = []
    for i in range(200):
        nas = Nas(nasname=f"nas{i}", shortname="sh", secret="se")
        nases.append(nas)
        repositories.nas.remove(nas.nasname)
        repositories.nas.add(nas)

    assert len(repositories.nas.find()) == 100  # limits defaults to 100
    assert len(repositories.nas.find(limit=20)) == 20
    assert len(repositories.nas.find(limit=None)) == 200  # all results

    assert repositories.nas.find(nasname_like="nas5%") == [nases[5]] + nases[50:60]  # nas5, nas50-59
    assert repositories.nas.find(nasname_gt="nas9") == nases[90:100]  # nas90-99
    assert repositories.nas.find(nasname_like="nas5%", nasname_gt="nas55") == nases[56:60]  # nas56-59

    assert repositories.nas.find(limit=5, nasname_like="nas5%") == [nases[5]] + nases[50:54]  # nas5, nas50-53
    assert repositories.nas.find(limit=5, nasname_gt="nas9") == nases[90:95]  # nas90-94

    assert repositories.nas.find(limit=5, nasname_gt="nas55", nasname_like="nas5%") == nases[56:60]  # nas56-59

    for nas in nases:
        repositories.nas.remove(nas.nasname)


def test_usergroup(repositories):
    group = Group(groupname="grp", checks=checks)
    user = User(username="usr", checks=checks, groups=[UserGroup(groupname=group.groupname)])

    # adding
    repositories.group.add(group)
    repositories.user.add(user)
    assert repositories.group.has_users(group.groupname)  # group has users

    # modifying
    repositories.user.set(user.username, new_groups=[])
    assert repositories.user.find_one(user.username).groups == []
    repositories.user.set(user.username, new_groups=[UserGroup(groupname=group.groupname)])
    assert repositories.user.find_one(user.username).groups == user.groups

    # removing
    repositories.user.remove(user.username)
    assert not repositories.group.has_users(group.groupname)  # group has no users
    repositories.group.remove(group.groupname)


def test_groupuser(repositories):
    user = User(username="usr", checks=checks)
    group = Group(groupname="grp", checks=checks, users=[GroupUser(username=user.username)])

    # adding
    repositories.user.add(user)
    repositories.group.add(group)
    assert repositories.group.has_users(group.groupname)  # group has users

    # modifying
    repositories.group.set(group.groupname, new_users=[])
    assert repositories.group.find_one(group.groupname).users == []
    repositories.group.set(group.groupname, new_users=[GroupUser(username=user.username)])
    assert repositories.group.find_one(group.groupname).users == group.users

    # removing
    repositories.user.remove(user.username)
    assert not repositories.group.has_users(group.groupname)  # group has no users
    repositories.group.remove(group.groupname)
