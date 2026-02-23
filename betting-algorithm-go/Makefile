.PHONY: build run test clean fmt vet lint

BINARY_NAME=bet4me-server
BUILD_DIR=bin

build:
	go build -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/server/

run: build
	./$(BUILD_DIR)/$(BINARY_NAME)

test:
	go test ./... -v -race

test-cover:
	go test ./... -coverprofile=coverage.out
	go tool cover -html=coverage.out -o coverage.html

fmt:
	go fmt ./...

vet:
	go vet ./...

clean:
	rm -rf $(BUILD_DIR) coverage.out coverage.html

deps:
	go mod tidy
	go mod download
