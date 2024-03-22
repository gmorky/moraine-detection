import ee

# Set resampling method on image collection
def set_resampling_method_on_collection(image, method):
    return image.resample(method)

# Input should be a Landsat 8 surface reflectance image
# Uses pixel quality (from CFMASK algorithm) and radiometric saturation QA to mask unwanted pixels
def scale_and_mask_landsat8_sr(image, do_mask):

    # Apply the scaling factors to the appropriate bands
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)

    # Masks
    # Bit 0 - Fill
    # Bit 1 - Dilated Cloud
    # Bit 2 - Cirrus
    # Bit 3 - Cloud
    # Bit 4 - Cloud Shadow
    if do_mask:
        qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
        saturationMask = image.select('QA_RADSAT').eq(0)

    # Replace the original bands with the scaled ones
    image = image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)

    # Apply the masks
    if do_mask:
        image = image.updateMask(qaMask).updateMask(saturationMask)

    return image

# Mask unwanted pixels and take median of the collection to create a composite
def create_composite_landsat8_sr(collection, do_mask):
    collection = collection.map(lambda image: scale_and_mask_landsat8_sr(image, do_mask))
    return collection.median()

# Convert moraine outlines to a binary mask
def create_moraines_mask(asset_path, filter, make_binary):

    # Pull in outlines and apply filter (if want to include/exclude some outlines)
    moraines_outlines = ee.FeatureCollection(asset_path).filter(filter)

    # Make mask. Pixels in the mask will be set to feature "label" attribute values
    moraines_mask = moraines_outlines.reduceToImage(['label'], ee.Reducer.first())

    # Do this if we want the mask to be 0s and 1s only (all values greater than 0 will be set to 1)
    if make_binary:
        moraines_mask = moraines_mask.where(moraines_mask.gt(0), 1)

    return moraines_mask

# Fetch pixels from google servers
def fetch_pixels(patch):

    # Parse
    image = patch['image']
    file_format = patch['file_format']
    width = patch['width']
    height = patch['height']
    scale_x = patch['scale_x']
    scale_y = patch['scale_y']
    translate_x = patch['translate_x']
    translate_y = patch['translate_y']
    crs = patch['crs']
    name = patch['name']
    id = patch['id']

    # Make request object
    request = {
        'expression': image,
        'fileFormat': file_format,
            'grid': {
            'dimensions': {
                'width': int(abs(width / scale_x)),
                'height': int(abs(height / scale_y))
            },
            'affineTransform': {
                'scaleX': scale_x,
                'shearX': 0,
                'translateX': translate_x,
                'shearY': 0,
                'scaleY': scale_y,
                'translateY': translate_y
            },
            'crsCode': crs,
        }
    }

    # Fetch pixels
    pixels = ee.data.computePixels(request)

    # Return pixels and patch info (for naming image file)
    return {'pixels': pixels, 'name': name, 'id': id}