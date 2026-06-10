# def my_range(stop: int, step: int = 1, start: int = 0):
#     i = start
#     while i < stop: 
#         i += step
#         yield i

# for i in my_range(stop=10, step=2, start=3):
#     print(i)

def fibbonachi():
    a = 0
    b = 1
    c = 0
    while True:
        c = a + b
        yield c
        b = a
        a = c
        
        
fib = fibbonachi()

for i in range(10):
    print(next(fib))
# def my_gen(a: int):
#     yield 1

#     if a == 2:
#         yield 4

#     print ("После 1")

#     yield 2 

#     print ("После 2")

#     if a != 2:
#         yield 3

    

# test = my_gen(2)
# for i in test:
#     print(i)