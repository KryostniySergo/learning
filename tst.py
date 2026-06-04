def my_gen(a: int):
    yield 1

    if a == 2:
        yield 4

    print ("После 1")

    yield 2 

    print ("После 2")

    if a != 2:
        yield 3

    

test = my_gen(2)
for i in test:
    print(i)