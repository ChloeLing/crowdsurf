
#include <iostream>
#include <stdlib.h>
#include <unistd.h>

using namespace std;

int segfault()
{
  cerr << "floating point exception" << endl;
  cout << 1/0 << endl;
  return -11;
}

int succeed(int amount) {
  for (int i=0; i<amount; i++) {
    cout << 0;
    cerr << 1;
  }
  return 0;
}

int main(int argc, char *argv[])
{
  enum {
    SEGFAULT, SUCCEED
  } mode = SUCCEED;
  int amount = 0;

  int c;
  while ((c = getopt(argc, argv, "fa:")) != -1) {
    switch (c) {
    case 'a':
      amount = atoi(optarg);
      break;
    case 'f':
      mode = SEGFAULT;
      break;
    default:
      abort();
    }
  }

  switch (mode) {
  case SEGFAULT:
    return segfault();
  case SUCCEED:
    return succeed(amount);
  }
}
