# Setup Instructions

Due to the Pydantic v2 update, you need to install the new requirements:

```bash
pip install -r requirements.txt
```

Or specifically install the pydantic-settings package:

```bash
pip install pydantic-settings==2.1.0
```

After installing, run the test script again:

```bash
python test_setup.py
```

This should resolve the import error for BaseSettings.