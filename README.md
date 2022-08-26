# State Machines

This code was a way for me to experiment with implementing state machines in Python. I would typically use enumerations for this purpose but what was more novel about my approach here is I would leverage metaclass functionality to validate expectations for subclasses of StateMachineBase.

The gumball machine is a simple example but the CSV parser is a more interesting situation as one cannot just interpret every comma as the end of a field or newline as the end of a record. The format I allow can have double quotes surrounding the field allowing for embedded commas or newlines or even embedded literal double quote
characters if the pair are contiguous. To prove I am getting the proper results, I included several test files.

Since I use the match feature, this requires Python 3.10+.