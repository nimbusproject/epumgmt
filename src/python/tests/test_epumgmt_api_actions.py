import epumgmt.api.actions


def test_expand_alias():
    actions = epumgmt.api.actions.ACTIONS()

    expanded = actions.expand_alias(actions.help)
    assert expanded == actions.HELP

    # Test when someone does something silly
    expanded = actions.expand_alias("all_actions")
    assert expanded == None

    # Test when someone expands something non-existant
    expanded = actions.expand_alias("fake")
    assert expanded == None
