# -*- coding: utf-8 -*-
#
# This file is part of RestAuthCommon.
#
# RestAuthCommon is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# RestAuthCommon is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with RestAuthCommon. If
# not, see <http://www.gnu.org/licenses/>.

"""
Exceptions related to RestAuth communication.

.. moduleauthor:: Mathias Ertl <mati@restauth.net>
"""


class RestAuthException(Exception):
    """Common base class for all Exceptions in this module."""
    response_code = 500


class RestAuthImplementationException(RestAuthException):
    """Base class for errors that should not occur in a production environment.

    If you ever catch such an exception, it is most likely due to a buggy client or server
    implementation.
    """


class BadRequest(RestAuthImplementationException):
    """Thrown when RestAuth was unable to parse/find the required request parameters.

    On a protocol level, this represents HTTP status code 400.
    """
    response_code = 400


class MarshalError(RestAuthImplementationException):
    """Thrown if data can't be marshalled."""
    response_code = 400


class UnmarshalError(RestAuthImplementationException):
    """Thrown if data can't be unmarshalled."""
    response_code = 400


class RestAuthSetupException(RestAuthException):
    """Base class for errors that should not occur in an correctly configured environment."""
    pass


class Unauthorized(RestAuthSetupException):
    """Thrown when service authentication failed.

    On a protocol level, this represents HTTP status code 401.
    """
    response_code = 401


class Forbidden(RestAuthSetupException):
    """Thrown when authentication succeeded but the client is not allowed to perform the request.

    On a protocol level, this represents HTTP status code 403.
    """
    response_code = 403


class ContentTypeException(RestAuthSetupException):
    """Meta-class for Content-Type related exceptions."""
    pass


class NotAcceptable(ContentTypeException):
    """The current content type is not acceptable to the RestAuth service.

    On a protocol level, this represents HTTP status code 406.
    """
    response_code = 406


class UnsupportedMediaType(ContentTypeException):
    """The RestAuth service does not support the media type used by this client implementation.

    On a protocol level, this represents HTTP status code 415.
    """
    response_code = 415


class RestAuthRuntimeException(RestAuthException):
    """Base class for exceptions that may occur at runtime but are not related to user input.

    Any subclass of this exception may be thrown by every method that interacts with the RestAuth
    service.
    """
    pass


class InternalServerError(RestAuthRuntimeException):
    """Thrown when the RestAuth service has an Internal Server Error (HTTP status code 500)."""
    response_code = 500


class RestAuthError(RestAuthException):
    """Base class for exceptions related to input coming from the client application."""
    pass


class ResourceNotFound(RestAuthError):
    """Thrown when a queried resource is not found."""
    response_code = 404

    def __init__(self, response=None):  # pragma: no cover
        """
        .. deprecated:: 0.7.0
           As this code only works on the client (and is never used), ResourceNotFound.response
           is deprecated and will be removed in 0.7.1.

        .. versionchanged:: 0.7.0
           The ``response`` parameter is optional and will be removed in 0.7.1.
        """
        self.response = response

    def get_type(self):  # pragma: no cover
        """Get the type of the queried resource that wasn't found.

        .. deprecated:: 0.7.0
           As this code only works on the client (and is never used), ResourceNotFound.response
           is deprecated and will be removed in 0.7.1.

        See the `specification
        <https://restauth.net/wiki/Specification#Resource-Type_header>`_ for
        possible values.

        :return: The resource type that causes this exception.
        :rtype: str
        """
        return self.response.getheader('Resource-Type')


class UserNotFound(ResourceNotFound):
    """Raised when a user was not found."""
    pass


class PropertyNotFound(ResourceNotFound):
    """Raised when a property was not found."""
    pass


class GroupNotFound(ResourceNotFound):
    """Raised when a group was not found."""
    pass


class ResourceConflict(RestAuthError):
    """Thrown when trying to create a resource that already exists.

    On a protocol level, this represents HTTP status code 409.
    """
    response_code = 409


class UserExists(ResourceConflict):
    """Raised when a user already exists."""
    pass


class PropertyExists(ResourceConflict):
    """Raised when a property already exists."""
    pass


class GroupExists(ResourceConflict):
    """Raised when a group already exists."""
    pass


class PreconditionFailed(RestAuthError):
    """Thrown when the submitted data was unacceptable to the system.

    This usually occurs when the username is invalid or the password is to short. On a protocol
    level, this represents HTTP status code 412.
    """
    response_code = 412
