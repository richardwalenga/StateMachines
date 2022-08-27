import src.csv_parser as CSV
import src.gumball_machine as GM
import src.state_machine as SM
import src.string_builder as SB
import functools
import logging
import sys
import unittest


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)


class StringBuilderTest(unittest.TestCase):
    def setUp(self):
        self.builder = SB.StringBuilder()

    def test(self):
        to_append = 'FooBarBaz'
        self.builder.append(to_append)
        self.assertEqual(to_append, str(self.builder))
        self.assertEqual(len(self.builder), len(to_append))

        another_append = '3'
        to_append += another_append
        self.builder.append(another_append)
        self.assertEqual(to_append, str(self.builder))
        self.assertEqual(len(self.builder), len(to_append))

        self.builder.clear()
        self.assertEqual(0, len(self.builder))

        another_string = 'Nyuk Nyuk'
        self.builder.append(another_string)
        self.assertEqual(another_string, str(self.builder))
        self.assertEqual(len(another_string), len(self.builder))

    def tearDown(self):
        self.builder.__exit__(None, None, None)


class InvalidStateMachineTest(unittest.TestCase):
    def test_failure(self):
        def with_no_states():
            class NoStates(SM.StateMachineBase):
                pass

        def with_non_enum_states():
            class NonEnumStates(SM.StateMachineBase):
                states = ('One', 'Two')

        def with_bad_initial_state():
            class BadInitialState(SM.StateMachineBase):
                states = GM.States
                initial_state = CSV.States.BEGIN

        self.assertRaises(TypeError, with_no_states)
        self.assertRaises(TypeError, with_non_enum_states)
        self.assertRaises(TypeError, with_bad_initial_state)
        with self.assertRaises(RuntimeError) as ctx:
            SM.StateMachineBase()
        self.assertTrue(str(ctx.exception).startswith(
            'StateMachineBase cannot'))


class GumballMachineTest(unittest.TestCase):
    def setUp(self):
        self.machine = GM.GumballMachine()

    def test_success(self):
        num_gumballs = 3
        self.assertEqual(GM.States.SOLD_OUT,
                         self.machine.__class__.initial_state)
        self.assertEqual(GM.States.SOLD_OUT, self.machine.state)
        self.machine.add_gumballs(num_gumballs)
        self.assertEqual(GM.States.NO_COIN, self.machine.state)
        self.machine.insert_coin()
        self.assertEqual(GM.States.HAS_COIN, self.machine.state)
        self.machine.insert_coin()
        self.assertEqual(GM.States.HAS_COIN, self.machine.state)
        self.machine.eject_coin()
        self.assertEqual(GM.States.NO_COIN, self.machine.state)
        self.machine.eject_coin()
        self.assertEqual(GM.States.NO_COIN, self.machine.state)
        self.machine.turn_crank()
        self.assertEqual(GM.States.NO_COIN, self.machine.state)

        for i in range(num_gumballs-1):
            self.machine.insert_coin()
            self.assertEqual(GM.States.HAS_COIN, self.machine.state)
            self.machine.turn_crank()
            self.assertEqual(GM.States.NO_COIN, self.machine.state)
            self.assertEqual(num_gumballs-i-1, self.machine.gumballs)

        self.machine.insert_coin()
        self.assertEqual(GM.States.HAS_COIN, self.machine.state)
        self.machine.turn_crank()
        self.assertEqual(GM.States.SOLD_OUT, self.machine.state)
        self.assertEqual(0, self.machine.gumballs)

        num_gumballs = 1
        self.machine.add_gumballs(num_gumballs)
        self.assertEqual(GM.States.NO_COIN, self.machine.state)
        self.assertEqual(num_gumballs, self.machine.gumballs)
        self.machine.insert_coin()
        self.assertEqual(GM.States.HAS_COIN, self.machine.state)
        self.machine.eject_coin()
        self.assertEqual(GM.States.NO_COIN, self.machine.state)
        self.machine.insert_coin()
        self.assertEqual(GM.States.HAS_COIN, self.machine.state)
        self.machine.turn_crank()
        self.assertEqual(GM.States.SOLD_OUT, self.machine.state)
        self.assertEqual(0, self.machine.gumballs)

    def test_failure(self):
        self.assertRaises(ValueError, functools.partial(
            self.machine.add_gumballs, 0))
        self.assertRaises(ValueError, functools.partial(
            self.machine.add_gumballs, -1))


class CsvParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CSV.CsvParser()

    def test_multiline(self):
        self.assertEqual(CSV.States.BEGIN, self.parser.__class__.initial_state)
        self.assertEqual(CSV.States.BEGIN, self.parser.state)
        records = None
        with open('multiline.csv', 'r') as multi:
            records = list(self.parser.parse(multi))
        self.assertEqual(2, self.parser.record_number)
        self.assertEqual(4, self.parser.fields_per_record)
        self.assertEqual(CSV.States.END, self.parser.state)
        self.assertEqual('""Great, "" Great', records[0][2])

        last_field_of_first_record = records[0][-1]
        self.assertTrue('\n' in last_field_of_first_record,
                        'The last field of the first record should span multiple lines.')
        self.assertEqual(
            '', records[1][1], 'A non-quoted field with nothing between the commas should be considered empty.')
        self.assertEqual(
            '', records[1][2], 'A quoted field with nothing in between the quotes should be considered empty.')

        last_field = records[-1][-1]
        self.assertEqual('Great', last_field)

        self.assertTrue(records[-1] is not self.parser.fields,
                         'The internal fields reference and the last record must not be the same')

        with self.assertRaises(IndexError, msg='There should be no record with an index of 2.') as ctx:
            records[self.parser.record_number]
        with self.assertRaises(IndexError, msg='-3 is too far from the end as there should be two records.') as ctx:
            records[-3]

        logger.info(f'Parsed: {repr(records)}')

    def test_malfomed(self):
        with open('malformed.csv', 'r') as f:
            with self.assertRaises(CSV.CsvParseException) as ctx:
                # force iteration to trigger exception
                list(self.parser.parse(f))
            exc_msg = str(ctx.exception)
            self.assertTrue(
                'Unbalanced double quote' in exc_msg and 'field 3 of record 1' in exc_msg)

    def _assert_parse_fails_with(self, filename: str, expected_exception: Exception) -> Exception:
        with self.assertRaises(expected_exception=expected_exception) as ctx:
            with open(filename, 'r') as f:
                # force iteration to trigger exception
                list(self.parser.parse(f))
        return ctx.exception

    def test_doublequote_not_field_end(self):
        exc_msg = str(self._assert_parse_fails_with(
            'doublequote-not-field-end.csv', CSV.CsvParseException))
        self.assertTrue(
            'Unexpected character   found after a double' in exc_msg and 'field 3 of record 1' in exc_msg)

    def test_doublequote_not_field_begin(self):
        exc_msg = str(self._assert_parse_fails_with(
            'doublequote-not-field-begin.csv', CSV.CsvParseException))
        self.assertTrue(
            'Unexpected double quote' in exc_msg and 'field 3 of record 1' in exc_msg)

    def test_non_contiguous_doublequotes_in_field(self):
        exc_msg = str(self._assert_parse_fails_with(
            'non-contiguous-doublequotes-in-field.csv', CSV.CsvParseException))
        self.assertTrue(
            'Unexpected character ! found after a double' in exc_msg and 'field 3 of record 2' in exc_msg)

    def test_field_count_mismatch(self):
        exc_msg = str(self._assert_parse_fails_with(
            'field-count-mismatch.csv', CSV.CsvParseException))
        self.assertEqual(
            'Record 2 has 4 fields but should have 3', exc_msg)


if __name__ == '__main__':
    unittest.main()
