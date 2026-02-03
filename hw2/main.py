from time import perf_counter
import sys

# increase the amount of output digits when converting a int to a string
sys.set_int_max_str_digits(0)


def fib(n):
    # Check for invalid lengths
    if type(n) is not int:
        raise TypeError('Input must be an integer')
    if n < 1:
        raise ValueError('Input must be positive')
    
    #set initial values
    n_prev = 0
    yield n_prev
    n_cur = 1
    n_next = 0

    for x in range(n):
        n_next = n_cur + n_prev
        yield n_cur
        n_prev = n_cur
        n_cur = n_next

if __name__ == "__main__":

    # testing reasonable sized string
    i = 0
    x = 20
    try: 
        for num in fib(x):
            print(f"the {i} value in the Fibonacci sequence is {num}")
            i += 1
    except ValueError:
        print("Invalid number entered")

    # 100,000 value test
    start = perf_counter()
    sum_threes = 0
    i = 0
    x = 100000
    try: 
        for num in fib(x):
            #print(num)
            if (i % 3 == 0):
                sum_threes += num
            i += 1
    except ValueError:
        print("Invalid number entered")
    end = perf_counter()

    print(f"The sum of every third Fibonacci number from 0 - {x} is {sum_threes}")
    print(f"Time taken for {x} values of the sequence: {end - start} seconds")

    # test graceful exit
    #for num in fib(-10):
    #    print(num)
    for num in fib("string"):
        print(num)
