def calculate (number):
    sum=0
    for n in range(1,number+1):
        sum=sum+n
    print("sum=",sum)

x=input("input:")
x=int(x)

calculate(x)

