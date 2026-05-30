from sys import*
setrecursionlimit(2000)
def F(n):
    if n>100000:
        return n
    if n<=100000:
        return F(n+1)+5*n+2
    


print(F(3)-F(7))
