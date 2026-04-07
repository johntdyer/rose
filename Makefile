APP=johntdyer/rose
VERSION=v$(shell cat build_number)

build:
	@docker build . -t $(APP):$(VERSION) && docker tag $(APP):$(VERSION) $(APP):latest
