#!/usr/bin/env python

from dm.common.constants.dmObjectLabels import DM_ID_KEY
from dm.common.constants.dmUserConstants import (
    DM_BADGE_KEY,
    DM_EMAIL_KEY,
    DM_FIRST_NAME_KEY,
    DM_IS_LOCAL_USER_KEY,
    DM_LAST_NAME_KEY,
    DM_LAST_UPDATE_KEY,
    DM_USERNAME_KEY,
)


# User Object Class
class UserInfo:
    def __init__(self, dbUser):
        self.badge = dbUser.get(DM_BADGE_KEY)
        if self.badge is None:
            self.badge = dbUser.get(DM_USERNAME_KEY)

        self.email = dbUser.get(DM_EMAIL_KEY)
        if self.email is None:
            self.email = ""

        self.firstName = dbUser.get(DM_FIRST_NAME_KEY)
        self.lastName = dbUser.get(DM_LAST_NAME_KEY)
        self.isLocalUser = dbUser.get(DM_IS_LOCAL_USER_KEY)
        self.lastUpdate = dbUser.get(DM_LAST_UPDATE_KEY)
        self.username = dbUser.get(DM_USERNAME_KEY)
        if self.username is None:
            self.username = "d" + self.badge

        self.id = dbUser.get(DM_ID_KEY)
        if self.id is None:
            self.id = ""

    def getBadge(self):
        return self.badge

    def getEmail(self):
        return self.email

    def getFirstName(self):
        return str(self.firstName)

    def getID(self):
        return int(self.id)

    def getIsLocalUser(self):
        return self.isLocalUser

    def getLastName(self):
        return str(self.lastName)

    def getLastUpdate(self):
        return self.lastUpdate

    def getUsername(self):
        return str(self.username)
