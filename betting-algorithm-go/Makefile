.PHONY: build test clean fmt vet lint run

BINARY_NAME=bet4me-server
GO=go

build:
	$(GO) build -o bin/$(BINARY_NAME) ./cmd/server/

test:
	$(GO) test ./... -v -count=1

test-short:
	$(GO) test ./... -short -count=1

fmt:
	$(GO) fmt ./...

vet:
	$(GO) vet ./...

lint: vet
	@echo "Lint passed (go vet)"

clean:
	rm -rf bin/
	$(GO) clean -cache

run: build
	./bin/$(BINARY_NAME)

coverage:
	$(GO) test ./... -coverprofile=coverage.out
	$(GO) tool cover -html=coverage.out -o coverage.html

tidy:
	$(GO) mod tidy
