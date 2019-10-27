def include_members(policy: dict, role_members: dict) -> (bool, dict):
    """
    Include a set of members with specific roles in an IAM policy.

    Args:
        policy:
            The policy to include the role members in.
        role_members:
            A mapping of role names to iterables of members.

    Returns:
        A two-element tuple containing a boolean indicating if the
        policy changed as a result of the member inclusion and the
        resulting IAM policy.
    """
    bindings = policy.get('bindings', [])
    is_modified = False

    # Track which roles have been found in the policy
    roles_found = {key: False for key in role_members.keys()}

    # Look for existing role bindings that need to be modified.
    for binding in bindings:
        role = binding.get('role')

        if role in role_members:
            roles_found[role] = True

            for member in role_members[role]:
                if member not in binding['members']:
                    is_modified = True
                    print(f"Need to add '{member}' to '{role}'")
                    binding['members'].append(member)

    # Add bindings for roles that did not yet have bindings
    for role, was_found in roles_found.items():
        if not was_found:
            is_modified = True
            print(f"Need binding for '{role}'")
            bindings.append({
                "members": list(role_members[role]),
                "role": role,
            })

    return is_modified, {"bindings": bindings}
