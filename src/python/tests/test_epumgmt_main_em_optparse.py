import epumgmt.main.em_optparse

def test_parse():
    from epumgmt.main.em_optparse import parse

    fake_command = "command"

    # Test Normal action
    test_action = "fake"
    cmd = "%s %s" % (fake_command, test_action)
    opts, _ = parse(cmd.split())

    assert opts.action == test_action


    # Test action with arbitrary hyphens
    test_action = "fake"
    cmd = "%s ---%s" % (fake_command, test_action)
    opts, _ = parse(cmd.split())

    assert opts.action == test_action


    # Test action with some options
    test_action = "fake"
    test_name = "testy"
    test_option = "--name %s" % test_name
    cmd = "%s %s %s" % (fake_command, test_action, test_option)
    opts, _ = parse(cmd.split())

    assert opts.action == test_action
    assert opts.name == test_name

