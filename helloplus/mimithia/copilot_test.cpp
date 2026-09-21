#include <iostream>
#include <vector>

std::vector<int> fibonacci(int n) {
    std::vector<int> fib_sequence;
    if (n <= 0) {
        return fib_sequence;
    }
    fib_sequence.push_back(0);
    if (n == 1) {
        return fib_sequence;
    }
    fib_sequence.push_back(1);
    for (int i = 2; i < n; ++i) {
        fib_sequence.push_back(fib_sequence[i - 1] + fib_sequence[i - 2]);
    }
    return fib_sequence;
}   

int main() {
    int n;
    std::cout << "Enter the number of Fibonacci numbers to generate: ";
    std::cin >> n;
    std::vector<int> fib_sequence = fibonacci(n);
    std::cout << "Fibonacci sequence: ";
    for (int num : fib_sequence) {
        std::cout << num << " ";
    }
    std::cout << std::endl;
    return 0;
}
