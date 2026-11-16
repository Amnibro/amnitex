/* On Windows, system() returns the command's exit code itself. */
#include "../../compat.h"
#ifndef WIFEXITED
#define WIFEXITED(s) 1
#define WEXITSTATUS(s) (s)
#define WIFSIGNALED(s) 0
#define WTERMSIG(s) 0
#endif
