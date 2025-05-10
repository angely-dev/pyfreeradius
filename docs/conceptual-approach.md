# Conceptual approach

You may be interested in the model-centric approach taken (or you may not).

**The implementation is fairly easy but it is good to know it conforms to some pattern.**

## Domain-Driven Design (DDD)

I found similarities with the DDD and especially the **Repository pattern.** It is a well-known pattern, yet often poorly applied, particularly in CRUD apps where there is a one-to-one mapping between entities and the database. In that case, the Repository just adds an extra layer for nothing really. I found it well-suited here because the "raw" database schema differs from the object-oriented or the "business" view of the Domain (the subject area).

> A REPOSITORY represents all objects of a certain type as a conceptual set **(usually emulated).** It acts like a collection, except with more elaborate querying capability. Objects of the appropriate type are added and removed, and the machinery behind the REPOSITORY inserts them or deletes them from the database. **The easiest REPOSITORY to build has hard-coded queries with specific parameters.** These queries can be various: retrieving an ENTITY by its identity (…)
>
> — Domain-Driven Design: Tackling Complexity in the Heart of Software. Eric Evans

Repositories are responsible for mapping Domain Objects to the database where they get flattened in some way:

![image](https://user-images.githubusercontent.com/4362224/202743771-07877b22-da82-4967-8bd5-1e62bb2f1e9a.png)

The Domain Services call the repositories to implement the Domain Logic which cannot fit in the Domain Objects directly (typically, when fetching data from different repositories is required for validation purposes). As per the DDD, the Domain Objects are classified this way:

* **Entities:** they have an identity and a lifecycle interest (`User`, `Group` and `Nas`)
* **Value Objects:** they have no conceptual identity and are Entity characteristics (`AttributeOpValue`)
* **Aggregate Root:** set of Entities and Value Objects with a well-defined boundary, the root being an Entity (a repository is then designed for each Aggregate Root)

`User` and `Group` are Aggregate Roots (they both aggregate check and reply attributes). `Nas` is also an Aggregate Root (it has its own boundary). Moreover, `User` and `Group` being linked together, this will produce some kind of association-class. In such a case, it is preferable to reference aggregates "by identity" to prevent boundary crossing:

> Prefer references to external aggregates only by their globally unique identity, not by holding a direct object reference (or “pointer”).
>
> — Effective Aggregate Design, Part II: Making Aggregates Work Together. Vaughn Vernon

The Domain Services can then be called by multiple Applications (say, a CLI app or a REST API app like [freeradius-api](https://github.com/angely-dev/freeradius-api)).

## Class diagram

The UML class diagram brings an object-oriented view of the FreeRADIUS database schema (therefore, this is NOT a one-to-one mapping with that schema).

![uml-class-diagram](https://user-images.githubusercontent.com/4362224/202876207-bc272618-a8d8-407d-a5fe-a523aaf492e8.png)

As represented, the `AttributeOpValue` class should be ideally subclassed since the sets of supported attributes and operators differ between the subclasses. This could be implemented with Enums. However, for simplicity, I decided not to do it, mainly because it would have meant reinventing (or integrating in some way) the RADIUS dictionaries.

Also, I limited the `Nas` attributes but you can add more if needed, .e.g., `type`, `community`, etc.

### Semantic

The diagram must be interpreted as follows:

* A `User` may have `Check` or `Reply` attributes—if the user is deleted, so are its attributes
* A `Group` may have `Check` or `Reply` attributes—if the group is deleted, so are its attributes
* A `User` may belong to multiple `Group`—if the user is deleted, so are its belonging to groups
* A `Group` may contain multiple `User`—if the group is deleted, so are its belonging to users

> To prevent accidental deletion however (when a group still contains legit users), we can think of a flag like `ignoreUsers` to be passed.

* User groups are ordered by a `priority` which semantic is fully documented in the [rlm_sql](https://wiki.freeradius.org/modules/Rlm_sql) module
* The `Nas` could be a standalone class. Alternatively, we can consider it depends on `User` as NASes perform AAA requests on them. This choice will have no consequence on the implementation as per the UML standard:

> The presence of Dependency relationships in a model does not have any runtime semantic implications.

### Some common sense (expressed by the property modifiers)

* A `username` is like an ID (two users cannot share the same one)—hence the use of `{id}`
* A `groupname` is like an ID (two groups cannot share the same one)—hence the use of `{id}`
* A `nasname` is like an ID (two NASes cannot share the same one)—hence the use of `{id}`
* A `User` cannot belong twice to the same `Group`—hence the use of `{unique}`
* A `Group` cannot contain twice to the same `User`—hence the use of `{unique}`

### Domain logic

The main goal of `pyfreeradius` is to implement some logic to ensure data consistency.

This logic is gradually illustrated in the [HOWTO](../README.md#howto) with multiple examples. Here is below a summary.

#### User and Group instances

A `User` must have at least one `Check` or one `Reply` attribute, or must belong to at least one `Group`.

A `Group` must have at least one `Check` or one `Reply` attribute, or must contain at least one `User`.

Otherwise, they wouldn't exist in the database as per the FreeRADIUS schema.

#### Create operation

A creation of an item which already exists will result in an `AlreadyExists` error.

When creating a `User`, if one of the given groups does not exist, a `GroupNotFound` error will be raised unless  `allow_groups_creation` is enabled—in the latter case, this results in creating the missing groups (i.e., without any attributes and with only one user).

When creating a `Group`, if one of the given users does not exist, a `UserNotFound` error will be raised unless `allow_users_creation` is enabled—in the latter case, this results in creating the missing users (i.e., without any attributes and belonging to only one group).

> This logic also applies during the update operation.

#### Delete operation

A deletion of a nonexistent item will result in a `NotFound` error.

When deleting a `User`, if it belongs to a group without any attributes and no other users, this group would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore); in this case, a `GroupWouldBeDeleted` error will be raised unless `prevent_groups_deletion` is disabled.

When deleting a `Group`, if it contains users, a `GroupStillHasUsers` error will be raised unless `ignore_users` is enabled—in the latter case, this results in deleting user belongings to the group (this, of course, won't delete users). Moreover, if the group to delete contains a user without any attributes and no other groups, this user would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore); in this case, a `UserWouldBeDeleted` error will be raised unless `prevent_users_deletion` is disabled.

> This logic also applies during the update operation.

#### Update operation

An update of a nonexistent item will result in a `NotFound` error.

When updating a `User`, if the new given fields result in a user without any attributes and no groups, this user would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore); in this case, a `UserWouldBeDeleted` error will be raised.

When updating a `Group`, if the new given fields result in a group without any attributes and no users, this group would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore); in this case, a `GroupWouldBeDeleted` error will be raised.

> TL;DR: the update logic is not trivial.
