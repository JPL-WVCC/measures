# msas_lambda_funcs

## adding external libraries
```
cd msas_lambda_funcs
pip install -t <lib> .
```

For example to install `requests`
```
cd msas_lambda_funcs
pip install -t requests .
```

## create deployment package
```
cd msas_lambda_funcs
zip -r -9 ../msas_lambda_funcs.zip *
```
