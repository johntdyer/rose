#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usage:
 rose <person> [--detailed] [--directsonly|--reverse] [--json] [--exclude-upn=<prefix>] [--exclude-empty-title]

Options:
  -h --help               Show this screen.
  --version               Show version.
  --detailed              Include additional details in output.
  --directsonly           Only list the target and their current directs.
  --reverse               Find the reporting chain above.
  --json                  Output results as JSON.
  --exclude-upn=<prefix>  Exclude accounts whose UPN starts with prefix (e.g. "svc.").
  --exclude-empty-title   Exclude accounts with no title set.
"""

from docopt import docopt
import json
import os
import ldap3
from ldap3.core.exceptions \
    import LDAPBindError, LDAPPasswordIsMandatoryError, LDAPSocketOpenError
import ssl
import sys


# Constants ..................................................................

ENV_HOST = 'ROSE_HOST'
ENV_PORT = 'ROSE_PORT'
ENV_UNAME = 'ROSE_UNAME'
ENV_PWORD = 'ROSE_PWORD'
ENV_SEARCH_BASE = 'ROSE_SEARCH_BASE'

SEARCH_ATTRS = [
    'distinguishedName', 'sAMAccountName', 'userPrincipalName',
    'objectClass', 'objectCategory',
    'cn', 'name', 'title', 'mail', 'department', 'directReports', 'manager',
    'memberOf']
# SEARCH_ATTRS = ['*']


# Functions ..................................................................


def get_person_dn(conn, basedn, sAMAccountName):
    '''
    Returns the person's DN given the connection, basedn, and sAMAccountName
    '''
    results = conn.search(
        basedn,
        "(&(objectClass=person)(sAMAccountName={}))".format(sAMAccountName),
        attributes=SEARCH_ATTRS)

    if results:
        if len(conn.entries) > 1:
            # Only expect one result.
            raise Exception('Found more than one result.')
        return conn.entries[0]
    else:
        raise Exception("No results found.")


def get_person_dn_by_email(conn, basedn, email):
    '''
    Returns the person's DN given the connection, basedn, and email instead
    of sAMAccountName
    '''
    results = conn.search(
        basedn,
        "(&(objectClass=person)(mail={}))".format(email),
        attributes=SEARCH_ATTRS)

    if results:
        if len(conn.entries) > 1:
            # Only expect one result.
            raise Exception('Found more than one result.')
        return conn.entries[0]
    else:
        raise Exception("No results found.")


def print_person(conn, basedn, targetdn, prefix, detailed):
    # print(targetdn)
    # return
    if detailed is True:
        print('{}"{}", "{}", "{}", "{}"'.format(
            prefix, targetdn.name,
            targetdn.userPrincipalName,
            targetdn.mail,
            targetdn.title,
            ))
    else:
        print('{}{}'.format(prefix, targetdn.name))
    return


def is_excluded(entry, exclude_upn, exclude_empty_title):
    if exclude_upn and str(entry.userPrincipalName).startswith(exclude_upn):
        return True
    if exclude_empty_title and str(entry.title) == '[]':
        return True
    return False


def print_person_and_directs(
        conn, basedn, targetdn, prefix,
        detailed=False, directs_only=False, exclude_upn=None, exclude_empty_title=False):

    print_person(conn, basedn, targetdn, prefix, detailed)
    if 'directReports' not in targetdn:
        return

    new_prefix = prefix + '    '
    for directReport in sorted(targetdn.directReports.values):
        matches = ["DisabledAccounts", "Disabled Users"]
        if any(x in directReport for x in matches):
            # TODO: Seems like something that wont be the same for everyone.
            continue

        results = conn.search(
            search_base=directReport,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=SEARCH_ATTRS)
        if not results:
            continue  # No results for this direct, continue with the list.

        if is_excluded(conn.entries[0], exclude_upn, exclude_empty_title):
            continue

        if directs_only:
            print_person(conn, basedn, conn.entries[0], new_prefix, detailed)
        else:
            print_person_and_directs(
                conn, basedn, conn.entries[0], new_prefix,
                detailed, directs_only, exclude_upn, exclude_empty_title)


def print_person_and_above(
        conn, basedn, targetdn, prefix, detailed=False):

    print_person(conn, basedn, targetdn, prefix, detailed)
    if 'manager' not in targetdn:
        return
    elif targetdn.distinguishedname == targetdn.manager:
        return

    results = conn.search(
        search_base="{}".format(targetdn.manager),
        search_filter="(objectClass=*)",
        search_scope=ldap3.BASE,
        attributes=SEARCH_ATTRS)
    if not results:
        return

    new_prefix = prefix + '    '
    print_person_and_above(conn, basedn, conn.entries[0], new_prefix, detailed)


def person_to_dict(entry):
    return {
        'name': str(entry.name),
        'upn': str(entry.userPrincipalName),
        'mail': str(entry.mail),
        'title': str(entry.title),
    }


def build_person_and_directs(conn, targetdn, directs_only=False, exclude_upn=None, exclude_empty_title=False):
    node = person_to_dict(targetdn)
    if 'directReports' not in targetdn:
        return node

    directs = []
    for directReport in sorted(targetdn.directReports.values):
        matches = ["DisabledAccounts", "Disabled Users"]
        if any(x in directReport for x in matches):
            continue
        results = conn.search(
            search_base=directReport,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=SEARCH_ATTRS)
        if not results:
            continue
        entry = conn.entries[0]
        if is_excluded(entry, exclude_upn, exclude_empty_title):
            continue
        if directs_only:
            directs.append(person_to_dict(entry))
        else:
            directs.append(build_person_and_directs(conn, entry, directs_only, exclude_upn, exclude_empty_title))

    node['directs'] = directs
    return node


def build_person_and_above(conn, targetdn):
    node = person_to_dict(targetdn)
    if 'manager' not in targetdn:
        return node
    elif targetdn.distinguishedname == targetdn.manager:
        return node

    results = conn.search(
        search_base="{}".format(targetdn.manager),
        search_filter="(objectClass=*)",
        search_scope=ldap3.BASE,
        attributes=SEARCH_ATTRS)
    if not results:
        return node

    node['manager'] = build_person_and_above(conn, conn.entries[0])
    return node


# Main .......................................................................

def main():
    '''
    Convenient main method.
    '''
    try:
        file_path = os.path.dirname(os.path.realpath(__file__))
        f = open('{}/build_number'.format(file_path), 'r')
        build_number = f.read().strip()
    except Exception:
        build_number = 0

    arguments = docopt(__doc__, version='ROSE v{}'.format(build_number))
    target_person = arguments['<person>']
    detailed = arguments['--detailed']
    directs_only = arguments['--directsonly']
    reverse = arguments['--reverse']
    as_json = arguments['--json']
    exclude_upn = arguments['--exclude-upn']
    exclude_empty_title = arguments['--exclude-empty-title']

    # Pull in host, port information from the environment variables.
    if ENV_HOST not in os.environ or ENV_PORT not in os.environ:
        print('Please set {} and {} in the env.'.format(ENV_HOST, ENV_PORT))
        sys.exit(1)
    if ENV_UNAME not in os.environ or ENV_PWORD not in os.environ:
        print('Please set {} and {} in the env.'.format(ENV_UNAME, ENV_PWORD))
        sys.exit(1)
    if ENV_SEARCH_BASE not in os.environ:
        print('Please set {} in the env.'.format(ENV_SEARCH_BASE))
        sys.exit(1)

    # Assign environment variables.
    target_host = os.getenv(ENV_HOST).strip()
    target_port = int(os.getenv(ENV_PORT))
    target_search_base = os.getenv(ENV_SEARCH_BASE).strip()
    target_uname = os.getenv(ENV_UNAME).strip()
    target_pword = os.getenv(ENV_PWORD).strip()

    # Check connectivity to the target LDAP server.
    try:
        tls_config = ldap3.Tls(
            validate=ssl.CERT_NONE,
            version=ssl.PROTOCOL_TLSv1_2)

        s = ldap3.Server(
            target_host,
            port=target_port,
            use_ssl=True,
            tls=tls_config,
            get_info=ldap3.NONE)

        c = ldap3.Connection(
                s,
                user=target_uname,
                password=target_pword,
                auto_bind=True,
                read_only=True)

        c.start_tls()
        c.bind()

    except TypeError as err:
        print(err)
        sys.exit(1)
    except (LDAPBindError,
            LDAPPasswordIsMandatoryError, LDAPSocketOpenError) as err:
        print("LDAP exception occurred:", err)
        sys.exit(1)
    except Exception as err:
        print("Exception occurred:", err)
        sys.exit(1)

    # Perform a basic search to obtain the DN of the given person.
    try:

        if "@" in target_person:
            dn = get_person_dn_by_email(c, target_search_base, target_person)
        else:
            dn = get_person_dn(c, target_search_base, target_person)

        if as_json:
            if not reverse:
                result = build_person_and_directs(c, dn, directs_only, exclude_upn, exclude_empty_title)
            else:
                result = build_person_and_above(c, dn)
            print(json.dumps(result, indent=2))
        elif not reverse:
            print_person_and_directs(
                c, target_search_base, dn, "", detailed, directs_only, exclude_upn, exclude_empty_title)
        else:
            print_person_and_above(
                c, target_search_base, dn, "", detailed
            )

    except Exception as err:
        print(err)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
