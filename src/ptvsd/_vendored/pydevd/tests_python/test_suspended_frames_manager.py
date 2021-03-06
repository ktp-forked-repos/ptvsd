import sys
from _pydevd_bundle.pydevd_constants import int_types
from _pydevd_bundle.pydevd_resolver import MAX_ITEMS_TO_HANDLE, TOO_LARGE_ATTR


def get_frame():
    var1 = 1
    var2 = [var1]
    var3 = {33: [var1]}
    return sys._getframe()


def check_vars_dict_expected(as_dict, expected):
    assert as_dict == expected


def test_suspended_frames_manager():
    from _pydevd_bundle.pydevd_suspended_frames import SuspendedFramesManager
    suspended_frames_manager = SuspendedFramesManager()
    py_db = None
    with suspended_frames_manager.track_frames(py_db) as tracker:
        # : :type tracker: _FramesTracker
        thread_id = 'thread1'
        frame = get_frame()
        tracker.track(thread_id, frame, frame_id_to_lineno={})

        assert suspended_frames_manager.get_thread_id_for_variable_reference(id(frame)) == thread_id

        variable = suspended_frames_manager.get_variable(id(frame))

        # Should be properly sorted.
        assert ['var1', 'var2', 'var3'] == [x.get_name()for x in variable.get_children_variables()]

        as_dict = dict((x.get_name(), x.get_var_data()) for x in variable.get_children_variables())
        var_reference = as_dict['var2'].pop('variablesReference')
        assert isinstance(var_reference, int_types)  # The variable reference is always a new int.
        assert isinstance(as_dict['var3'].pop('variablesReference'), int_types)  # The variable reference is always a new int.

        check_vars_dict_expected(as_dict, {
            'var1': {'name': 'var1', 'value': '1', 'type': 'int', 'evaluateName': 'var1', 'variablesReference': 0},
            'var2': {'name': 'var2', 'value': '[1]', 'type': 'list', 'evaluateName': 'var2'},
            'var3': {'name': 'var3', 'value': '{33: [1]}', 'type': 'dict', 'evaluateName': 'var3'}
        })

        # Now, same thing with a different format.
        as_dict = dict((x.get_name(), x.get_var_data(fmt={'hex': True})) for x in variable.get_children_variables())
        var_reference = as_dict['var2'].pop('variablesReference')
        assert isinstance(var_reference, int_types)  # The variable reference is always a new int.
        assert isinstance(as_dict['var3'].pop('variablesReference'), int_types)  # The variable reference is always a new int.

        check_vars_dict_expected(as_dict, {
            'var1': {'name': 'var1', 'value': '0x1', 'type': 'int', 'evaluateName': 'var1', 'variablesReference': 0},
            'var2': {'name': 'var2', 'value': '[0x1]', 'type': 'list', 'evaluateName': 'var2'},
            'var3': {'name': 'var3', 'value': '{0x21: [0x1]}', 'type': 'dict', 'evaluateName': 'var3'}
        })

        var2 = dict((x.get_name(), x) for x in variable.get_children_variables())['var2']
        children_vars = var2.get_children_variables()
        as_dict = (dict([x.get_name(), x.get_var_data()] for x in children_vars))
        assert as_dict == {
            '0': {'name': '0', 'value': '1', 'type': 'int', 'evaluateName': 'var2[0]', 'variablesReference': 0 },
            '__len__': {'name': '__len__', 'value': '1', 'type': 'int', 'evaluateName': 'len(var2)', 'variablesReference': 0, 'presentationHint': {'attributes': ['readOnly']}, },
        }

        var3 = dict((x.get_name(), x) for x in variable.get_children_variables())['var3']
        children_vars = var3.get_children_variables()
        as_dict = (dict([x.get_name(), x.get_var_data()] for x in children_vars))
        assert isinstance(as_dict['33'].pop('variablesReference'), int_types)  # The variable reference is always a new int.

        check_vars_dict_expected(as_dict, {
            '33': {'name': '33', 'value': "[1]", 'type': 'list', 'evaluateName': 'var3[33]'},
            '__len__': {'name': '__len__', 'value': '1', 'type': 'int', 'evaluateName': 'len(var3)', 'variablesReference': 0, 'presentationHint': {'attributes': ['readOnly']}, }
        })


_NUMBER_OF_ITEMS_TO_CREATE = MAX_ITEMS_TO_HANDLE + 300


def get_dict_large_frame():
    obj = {}
    for idx in range(_NUMBER_OF_ITEMS_TO_CREATE):
        obj[idx] = (1)
    return sys._getframe()


def get_set_large_frame():
    obj = set()
    for idx in range(_NUMBER_OF_ITEMS_TO_CREATE):
        obj.add(idx)
    return sys._getframe()


def get_tuple_large_frame():
    obj = tuple(range(_NUMBER_OF_ITEMS_TO_CREATE))
    return sys._getframe()


def test_get_child_variables():
    from _pydevd_bundle.pydevd_suspended_frames import SuspendedFramesManager
    suspended_frames_manager = SuspendedFramesManager()
    py_db = None
    for frame in (
        get_dict_large_frame(),
        get_set_large_frame(),
        get_tuple_large_frame(),
        ):
        with suspended_frames_manager.track_frames(py_db) as tracker:
            # : :type tracker: _FramesTracker
            thread_id = 'thread1'
            tracker.track(thread_id, frame, frame_id_to_lineno={})

            assert suspended_frames_manager.get_thread_id_for_variable_reference(id(frame)) == thread_id

            variable = suspended_frames_manager.get_variable(id(frame))

            children_variables = variable.get_child_variable_named('obj').get_children_variables()
            assert len(children_variables) < _NUMBER_OF_ITEMS_TO_CREATE

            found_too_large = False
            found_len = False
            for x in children_variables:
                if x.name == TOO_LARGE_ATTR:
                    var_data = x.get_var_data()
                    assert 'readOnly' in var_data['presentationHint']['attributes']
                    found_too_large = True
                elif x.name == '__len__':
                    found_len = True

            if not found_too_large:
                raise AssertionError('Expected to find variable named: %s' % (TOO_LARGE_ATTR,))
            if not found_len:
                raise AssertionError('Expected to find variable named: __len__')

