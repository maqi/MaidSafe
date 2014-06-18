#
# The MIT License (MIT)
#
# Copyright (c) 2013 Matthew Arsenault
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

include(CheckCCompilerFlag)

set(CMAKE_REQUIRED_FLAGS "-Werror -fstack-protector-strong")
check_c_compiler_flag("-fstack-protector-strong" HAVE_FLAG_STACK_PROTECTOR_STRONG)
unset(CMAKE_REQUIRED_FLAGS)

if(HAVE_FLAG_STACK_PROTECTOR_STRONG)
  set(STACK_PROTECTOR_STRONG_FLAG "-fstack-protector-strong")
endif()

if(NOT STACK_PROTECTOR_STRONG_FLAG)
  return()
endif()

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${STACK_PROTECTOR_STRONG_FLAG}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${STACK_PROTECTOR_STRONG_FLAG}")
