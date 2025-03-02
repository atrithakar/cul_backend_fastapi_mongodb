#include "../test_module_1/mathss.h"

int addply(int a, int b) {
    int sum = add(a, b);
    int prod = multiply(sum, b);
    return prod;
}