from __future__ import annotations
from .io import each_character_of
from .state_machine import StateMachineBase
from .string_builder import StringBuilder
import enum
import io
import math


class States(enum.Enum):
    BEGIN = enum.auto()
    IN_FIELD = enum.auto()
    QUOTE_IN_FIELD = enum.auto()
    END_OF_FIELD = enum.auto()
    END_OF_RECORD = enum.auto()
    END = enum.auto()


class CsvParseException(Exception):
    pass


class CsvParser(StateMachineBase):
    """This is a class to parse CSV input into fields. The given
    CSV can have embedded newlines and commas in a field if it is
    surrounded by double-quotes. Any literal doube-quotes within
    the field must be escaped with a preceding double-quote."""
    __slots__ = ('fields', 'fields_per_record', 'doublequotes_in_field')

    states = States

    def __init__(self) -> None:
        """Constructor"""
        super().__init__()
        self.fields = []
        self.fields_per_record = None
        self.doublequotes_in_field = 0

    def __iter__(self):
        """Provides a way to iterate the parsed CSV by record.

        Yields:
            list: A list of strings representing the fields
            making up a record.
        """
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, key):
        """Supports the bracket syntax to retrieve a list
        of fields for a record. This does support negative
        indexing (-1 represents the last record).

        Args:
            key: The 0-based index of the desired record.

        Raises:
            TypeError: Raised if key is not an integer as
            it is simpler to implement if we don't accept
            slices.
            IndexError: Raised for a key out of range.

        Returns:
            The list of fields for the record.
        """
        if not isinstance(key, int):
            raise TypeError('key must be an integer')

        field_count = len(self.fields)
        err = IndexError('record index out of range')
        start_index = 0
        if key < 0:
            if field_count <= self.fields_per_record:
                raise err
            factor = math.trunc(field_count / self.fields_per_record) + key
            if factor < 0:
                raise err
            start_index = factor*self.fields_per_record
        else:
            start_index = key * self.fields_per_record
            if start_index >= field_count:
                raise err
        return self.fields[start_index:start_index+self.fields_per_record]

    def __len__(self) -> int:
        """Returns the record count.

        Returns:
            int: Record count.
        """
        return 0 if len(self.fields) == 0 else self.record_number

    @property
    def record_number(self) -> int:
        """Gives the current record number starting from one.

        Returns:
            int: The current record number.
        """
        if self.fields_per_record is None:
            return 1
        return math.ceil(len(self.fields) / self.fields_per_record)

    @property
    def has_unbalanced_doublequotes(self) -> bool:
        """Returns true if there are an odd number of
        double quotes in the current field. This could
        indicate a literal double quote is should be
        part of the parsed field or the input is malformed.

        Returns:
            bool: True when there are an odd number of double quotes.
        """
        return self.doublequotes_in_field % 2 == 1

    def end_field(self, builder: StringBuilder) -> None:
        """Finishes the current field.

        Args:
            builder (StringBuilder): Holds field contents.
        """
        if self.doublequotes_in_field > 0:
            if self.has_unbalanced_doublequotes:
                raise CsvParseException(f'Field {len(self.fields)+1} in Record {self.record_number} has unbalanced double-quotes')
            if not self.state == States.QUOTE_IN_FIELD:
                raise CsvParseException(f'Field {len(self.fields)+1} in Record {self.record_number} must end with a double-quote')
            self.doublequotes_in_field = 0
        self.fields.append(str(builder))
        builder.clear()
        self.transition(States.END_OF_FIELD)

    def check_for_invalid_number_of_fields(self) -> None:
        """Ensures the number of fields is consistent for each
        record found in the csv input.

        Raises:
            CsvParseException: Raised when subsequent records
            don't have the same number of fields as the first.
        """
        fields_discrepancy = len(self.fields) % self.fields_per_record
        if fields_discrepancy == 0:
            return
        raise CsvParseException(
            f'Record {self.record_number} has {fields_discrepancy} fields but should have {self.fields_per_record}')

    def end_record(self, builder: StringBuilder) -> None:
        """Finishes the current record.

        Args:
            builder (StringBuilder): Holds field contents.
        """
        self.end_field(builder)
        self.transition(States.END_OF_RECORD)
        # After the first unembedded newline is processed, we
        # need to record the number of fields in this record to
        # verify against subsequent records.
        if self.fields_per_record is None:
            self.fields_per_record = len(self.fields)
            return
        self.check_for_invalid_number_of_fields()

    def process_char(self, ch: str, builder: StringBuilder) -> None:
        """Processes the next character.

        Args:
            ch (str): The character to process.
            builder (StringBuilder): Holds field content.
        """
        if self.state == States.QUOTE_IN_FIELD:
            # We most recently found a double-quote which
            # was not at the very beginning of the field.
            # In most caess we have to defer until we know
            # the next non-doublequote character in order to
            # avoid outputting a double-quote in a situation
            # like this which should obviously represent an
            # empty field:  ...,"",...
            if self.has_unbalanced_doublequotes:
                builder.append('"')

        if ch == ',':
            if not self.has_unbalanced_doublequotes:
                self.end_field(builder)
                return
        elif ch == '\n':
            if self.has_unbalanced_doublequotes:
                # makes multi-line fields possible
                builder.append(ch)
            else:
                self.end_record(builder)
            return

        if self.state == States.QUOTE_IN_FIELD and not self.has_unbalanced_doublequotes:
            raise CsvParseException(f'Unexpected character {ch} found after a double-quote in field {len(self.fields)+1} of record {self.record_number}')

        if self.state != States.IN_FIELD:
            self.transition(States.IN_FIELD)
        builder.append(ch)

    def process_doublequote(self, builder: StringBuilder) -> None:
        """Handles a double-quote.

        Args:
            builder (StringBuilder): Holds field content.

        Raises:
            CsvParseException: Raised if a double-quote is not
            found at the very beginning and end of a field.
        """
        match self.state:
            case (States.BEGIN | States.END_OF_FIELD | States.END_OF_RECORD):
                self.doublequotes_in_field = 1
                self.transition(States.IN_FIELD)
            case States.IN_FIELD:
                if self.doublequotes_in_field == 0:
                    raise CsvParseException(
                        f'Unexpected double-quote found in record {self.record_number} at position {len(builder)+1} of field {len(self.fields)+1}')
                self.doublequotes_in_field += 1
                self.transition(States.QUOTE_IN_FIELD)
            case States.QUOTE_IN_FIELD:
                self.doublequotes_in_field += 1
                # One cannot indefinitely defer the output of
                # literal doublequote characters until a 
                # non-doublequote character is found as this
                # is a strange but valid situation:
                # ...," """""" ",...
                if self.has_unbalanced_doublequotes:
                    builder.append('"')
                self.transition(States.IN_FIELD)
            case other:
                raise CsvParseException(f'Unexpected state {other}')

    def parse(self, read_from: io.TextIOBase):
        """Parses the given CSV input into fields.

        Args:
            read_from (io.TextIOBase): The stream of CSV input.

        Raises:
            CsvParseException: Raised if the given text cannot
            be successfully parsed.
        """
        with StringBuilder() as builder:
            for c in each_character_of(read_from):
                match c:
                    case '"':
                        self.process_doublequote(builder)
                    case _:
                        self.process_char(c, builder)
            if self.state != States.END_OF_RECORD:
                self.end_record(builder)
            self.transition(States.END)

    def reset(self) -> None:
        """Resets the parser to its initial state."""
        super().reset()
        self.fields = []
        self.fields_per_record = None
        self.doublequotes_in_field = 0
