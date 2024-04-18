import psycopg2

def conn_to_db():

  conn = psycopg2.connect(database = "tempdb", 
                          user = "myuser", 
                          host= 'test-db.aan0943.aws.amazon.com',
                          password = "Test1234!",
                          port = 5432)

  cursor = conn.cursor()

  cursor.execute("select version()")

  data = cursor.fetchone()
  print("Connection established to: ",data)

  conn.close()

def inverted_star_pattern_recursive(height):
    if height > 0:
        print("*" * height)
        inverted_star_pattern_recursive(height - 1)
 
height = 5
inverted_star_pattern_recursive(height)

def insertionSortRecursive(arr, n):
    # base case
    if n <= 1:
        return
 
    # Sort first n-1 elements
    insertionSortRecursive(arr, n - 1)
 
    # Insert last element at its correct position in sorted array.
    last = arr[n - 1]
    j = n - 2
 
    # Move elements of arr[0..i-1], that are
    # greater than key, to one position ahead
    # of their current position
    while (j >= 0 and arr[j] > last):
        arr[j + 1] = arr[j]
        j = j - 1
    arr[j + 1] = last
 
 
# Driver program to test insertion sort
if __name__ == '__main__':
    A = [-7, 11, 6, 0, -3, 5, 10, 2]
    n = len(A)
    insertionSortRecursive(A, n)
    print(A)
 
