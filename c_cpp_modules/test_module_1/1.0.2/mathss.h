int add(int a, int b)
{
    return a + b;
}

int subtract(int a, int b)
{
    return a - b;
}

int multiply(int a, int b)
{
    return a * b;
}

int divide(int a, int b)
{
    return a / b;
}

int pow(int a, int b){
    int prod = 1;
    for(int i = 0; i < b; i++) {
        prod*=a;
    }
    return prod;
}

int square(int a) {
    return a*a;
}