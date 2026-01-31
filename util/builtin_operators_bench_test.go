// Copyright 2017 The casbin Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package util

import "testing"

// Benchmark KeyMatch2 without wildcard (fast path)
func BenchmarkKeyMatch2_NoWildcard(b *testing.B) {
	key1 := "/api/users/123"
	key2 := "/api/users/:id"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch2(key1, key2)
	}
}

// Benchmark KeyMatch2 with wildcard (original path)
func BenchmarkKeyMatch2_WithWildcard(b *testing.B) {
	key1 := "/api/users/123/posts"
	key2 := "/api/users/:id/*"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch2(key1, key2)
	}
}

// Benchmark KeyMatch2 static path (fast path)
func BenchmarkKeyMatch2_StaticPath(b *testing.B) {
	key1 := "/api/users"
	key2 := "/api/users"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch2(key1, key2)
	}
}

// Benchmark KeyMatch3 without wildcard (fast path)
func BenchmarkKeyMatch3_NoWildcard(b *testing.B) {
	key1 := "/api/users/123"
	key2 := "/api/users/{id}"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch3(key1, key2)
	}
}

// Benchmark KeyMatch3 with wildcard (original path)
func BenchmarkKeyMatch3_WithWildcard(b *testing.B) {
	key1 := "/api/users/123/posts"
	key2 := "/api/users/{id}/*"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch3(key1, key2)
	}
}

// Benchmark KeyMatch3 static path (fast path)
func BenchmarkKeyMatch3_StaticPath(b *testing.B) {
	key1 := "/api/users"
	key2 := "/api/users"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch3(key1, key2)
	}
}

// Benchmark KeyMatch4 without wildcard (fast path)
func BenchmarkKeyMatch4_NoWildcard(b *testing.B) {
	key1 := "/parent/123/child/123"
	key2 := "/parent/{id}/child/{id}"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch4(key1, key2)
	}
}

// Benchmark KeyMatch4 with wildcard (original path)
func BenchmarkKeyMatch4_WithWildcard(b *testing.B) {
	key1 := "/parent/123/child/123/posts"
	key2 := "/parent/{id}/child/{id}/*"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch4(key1, key2)
	}
}

// Benchmark KeyMatch5 without wildcard (fast path)
func BenchmarkKeyMatch5_NoWildcard(b *testing.B) {
	key1 := "/api/users/123?status=1"
	key2 := "/api/users/{id}"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch5(key1, key2)
	}
}

// Benchmark KeyMatch5 with wildcard (original path)
func BenchmarkKeyMatch5_WithWildcard(b *testing.B) {
	key1 := "/api/users/123/posts?status=1"
	key2 := "/api/users/{id}/*"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch5(key1, key2)
	}
}

// Benchmark KeyGet2 without wildcard (fast path)
func BenchmarkKeyGet2_NoWildcard(b *testing.B) {
	key1 := "/api/users/123"
	key2 := "/api/users/:id"
	pathVar := "id"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyGet2(key1, key2, pathVar)
	}
}

// Benchmark KeyGet2 with wildcard (original path)
func BenchmarkKeyGet2_WithWildcard(b *testing.B) {
	key1 := "/api/users/123/posts"
	key2 := "/api/users/:id/*"
	pathVar := "id"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyGet2(key1, key2, pathVar)
	}
}

// Benchmark KeyGet3 without wildcard (fast path)
func BenchmarkKeyGet3_NoWildcard(b *testing.B) {
	key1 := "/api/users/123"
	key2 := "/api/users/{id}"
	pathVar := "id"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyGet3(key1, key2, pathVar)
	}
}

// Benchmark KeyGet3 with wildcard (original path)
func BenchmarkKeyGet3_WithWildcard(b *testing.B) {
	key1 := "/api/users/123/posts"
	key2 := "/api/users/{id}/*"
	pathVar := "id"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyGet3(key1, key2, pathVar)
	}
}

// Benchmark complex pattern without wildcard (fast path)
func BenchmarkKeyMatch2_ComplexNoWildcard(b *testing.B) {
	key1 := "/api/v1/projects/project1/resources/resource2/actions"
	key2 := "/api/v1/projects/:project/resources/:resource/actions"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch2(key1, key2)
	}
}

// Benchmark complex pattern with wildcard (original path)
func BenchmarkKeyMatch2_ComplexWithWildcard(b *testing.B) {
	key1 := "/api/v1/projects/project1/resources/resource2/extra/data"
	key2 := "/api/v1/projects/:project/resources/:resource/*"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		KeyMatch2(key1, key2)
	}
}
