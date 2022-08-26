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
        self.assertTrue(str(ctx.exception).startswith('StateMachineBase cannot'))


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
        self.assertEqual(0, len(self.parser))
        with open('multiline.csv', 'r') as multi:
            self.parser.parse(multi)
        self.assertEqual(2, self.parser.record_number)
        self.assertEqual(len(self.parser), self.parser.record_number)
        self.assertEqual(4, self.parser.fields_per_record)
        self.assertEqual(CSV.States.END, self.parser.state)
        self.assertEqual('""Great, "" Great', self.parser.fields[2])
        self.assertEqual(self.parser[0][2], self.parser.fields[2])

        last_field_of_first_record = self.parser.fields[self.parser.fields_per_record-1]
        self.assertTrue('\n' in last_field_of_first_record,
                        'The last field of the first record should span multiple lines.')
        self.assertEqual(self.parser[0][-1], last_field_of_first_record,
                         'The two-dimensional access of [0][1] should return the last field of the first record.')
        self.assertListEqual(
            self.parser[0], self.parser[-2], 'Negative indexing should work to target first record.')
        self.assertListEqual(
            self.parser[1], self.parser[-1], 'Negative indexing should work to target second record.')
        
        self.assertEqual('', self.parser[1][1], 'A non-quoted field with nothing between the commas should be considered empty.')
        self.assertEqual('', self.parser[1][2], 'A quoted field with nothing in between the quotes should be considered empty.')

        last_field = self.parser.fields[-1]
        self.assertEqual('Great', last_field)
        self.assertEqual(self.parser[-1][-1], last_field,
                         '[-1][-1] should retrieve the last field.')

        with self.assertRaises(IndexError, msg='There should be no record with an index of 2.') as ctx:
            self.parser[self.parser.record_number]
        with self.assertRaises(IndexError, msg='-3 is too far from the end as there should be two records.') as ctx:
            self.parser[-3]

        num_iterations = 0
        for record in self.parser:
            num_iterations += 1
            logger.info('Record %i\'s first value: %s',
                        num_iterations, record[0])
        self.assertEqual(num_iterations, self.parser.record_number)

    def test_malfomed(self):
        with open('malformed.csv', 'r') as f:
            self.assertRaises(CSV.CsvParseException,
                              functools.partial(self.parser.parse, f))

    def test_doublequote_not_field_end(self):
        with open('doublequote-not-field-end.csv', 'r') as f:
            self.assertRaises(CSV.CsvParseException,
                              functools.partial(self.parser.parse, f))

    def test_doublequote_not_field_begin(self):
        with open('doublequote-not-field-begin.csv', 'r') as f:
            self.assertRaises(CSV.CsvParseException,
                              functools.partial(self.parser.parse, f))

    def test_non_contiguous_doublequotes_in_field(self):
        with open('non-contiguous-doublequotes-in-field.csv', 'r') as f:
            self.assertRaises(CSV.CsvParseException,
                              functools.partial(self.parser.parse, f))

    def test_field_count_mismatch(self):
        with open('field-count-mismatch.csv', 'r') as f:
            self.assertRaises(CSV.CsvParseException,
                              functools.partial(self.parser.parse, f))


if __name__ == '__main__':
    unittest.main()
