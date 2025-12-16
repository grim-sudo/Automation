# Prime Number Identifier

def is_prime(num):
    """Check if a number is prime."""
    if num < 2:
        return False
    if num == 2:
        return True
    if num % 2 == 0:
        return False
    for i in range(3, int(num**0.5) + 1, 2):
        if num % i == 0:
            return False
    return True

def find_primes(limit):
    """Find all prime numbers up to the given limit."""
    primes = [num for num in range(2, limit + 1) if is_prime(num)]
    return primes

def find_primes_count(count):
    """Find the first n prime numbers."""
    primes = []
    num = 2
    while len(primes) < count:
        if is_prime(num):
            primes.append(num)
        num += 1
    return primes

if __name__ == "__main__":
    choice = input("Find primes by (1) limit or (2) count? Enter 1 or 2: ")
    
    if choice == "1":
        limit = int(input("Enter the upper limit: "))
        primes = find_primes(limit)
        print(f"Prime numbers up to {limit}: {primes}")
        print(f"Total primes found: {len(primes)}")
    elif choice == "2":
        count = int(input("Enter the count of primes to find: "))
        primes = find_primes_count(count)
        print(f"First {count} prime numbers: {primes}")
    else:
        print("Invalid choice!")
