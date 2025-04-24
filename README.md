# AI and machine learning challenges for improving planning data quality

This repository contains scenarios, test cases and code for challenges to scale how we improve the quality of data on https://planning.data.gov.uk

Testing and assuring our data quality is intended to complement our with work with [i.AI](https://ai.gov.uk/) to increase the availability of data by [extracting data from documents](https://github.com/digital-land/digital-land/issues/360).

We expect to incorporate issues identified by these tests into the feedback we give to [data providers](https://submit.planning.data.gov.uk/), to help them improve the availability and quality of their planning data.

# Getting Started

To use this repository, install it with `poetry install`. This will install the `data_quality_utils` module as well as all necessary dependencies. To use poetry with jupyter, either point your VSCode notebook environment to the new poetry installation or run jupyeter with `poetry run jupyter notebook`.

You can then run the notebooks in `notebooks/` to see how the functionality developed for `data_quality_utils` can be combined to meet the challenges. Each notebook contains explanatory text detailing the method used to complete the challenge, demonstrates the use of the reusable tools, and showcases the solution on a test data set.

# Challenges

## Finding and maintaining our links to information sources

The planning data platform collects data from local sources and them available as national datasets.

We link to an information page for each local data source, a webpage containing human readable information about the data.
This page MUST be on the authorititive website for the organisation.

As an example, most LPAs have a planning policy page listing its conservation areas:

* [Barnet conservation areas](https://www.barnet.gov.uk/planning-and-building-control/conservation-and-heritage/conservation-areas)
* [Liverpool conservation areas](https://liverpool.gov.uk/planning-and-building-control/trees-hedges-and-conservation/conservation-areas/)
* [Erewash conservation areas](https://www.erewash.gov.uk/planning-policy-section/conservation-areas.html)
* [Dacorum conservation areas](https://www.dacorum.gov.uk/home/planning-development/planning-cons-design/conservation-areas)
* [Lambeth conservation areas](https://www.lambeth.gov.uk/planning-and-building-control/conservation-and-listed-buildings/conservation-area-profiles)

We record a link to these source web pages as the `documentation-url` in our [source](https://digital-land.github.io/specification/dataset/source/) configuration.

Can we find a way to automatically locate the correct webpage for the `documentation-url` of an entity?

## Comparing entities against documents

In addition to the `documentation-url`, the webpage with human readable content describing the entity, from the above challenge, every entity has a `document-url`. This is usually a PDF containing the material information, including the `name` of the entity, a `start-date` (when the entity came into force) and where the entity applies. For example:

* The entity [6100046](https://www.planning.data.gov.uk/entity/6100046) represents an Article 4 Direction ([PDF](https://www.camden.gov.uk/documents/20142/4842163/South+Hill+Park+Article+4.pdf/47a3f006-5739-9ac3-363b-b0025e487ec4)). The direction removes permitted development rights from a single area represented by the entity [https://www.planning.data.gov.uk/entity/7010002601], found using a [datasette query](https://datasette.planning.data.gov.uk/article-4-direction-area?sql=select+entity%2C+prefix%2C+reference%2C+name%2C+geojson%2C+geometry%2C+json%2C+%0D%0A++json_extract+%28json%2C+%27%24.article-4-direction%27%29+AS+article_4_direction%2C+organisation_entity%2C+start_date%2C+end_date+from+entity+where+article_4_direction+%3D+%27A4SHP1%27).

Can we find a way to automatically collect the correct document from the authoritative website?

## Finding possible duplicate entities
Often, the same real world location such as a specific conservation area, is recorded multiple times in the planning data as different entities. There should be a 1:1 mapping between real entities and entity records in the data.

Can we find a way to automatically flag entities that are likely to be duplicates?

## Comparing boundaries to geographical features
Entities such as conservation areas have a geographic extent that is typically recorded in the relevant legal instrument (document-url). In order to make this more accessible, planning.data.gov.uk extracts the boundaries of the entity as a GPS polygon. The process for generating these can produce mistakes but without a ground truth polygon to compare to, it is difficult to indentify these. One sign that a polygon may be incorrect is when the boundary of the entity does not follow local geographic features.

For example, a conservation area may cover an area of farmland bounded on one side by a road and a woodland on the other. If the polygon broadly followed those boundaries but diverged from the woodland edge and cut off a corner of the farmland in the process, this error in the polygon data would be flagged by a system that could see the polygon does not follow the nearby geographic feature (the woodland).

Can we find a way to obtain polygons for geographic features and flag entities whose polygons do not follow the local features?

## Checking Tree Protection Orders
One key piece of data associated with a tree protect order is the location of the tree. In the planning data, this location is represented by a GPS co-ordinate. Errors can occur in this data in many ways but one clear sign that the data is wrong would be if there was no tree at the listed co-ordinates.

Can we find a way to automatically detect whether a tree is present at a GPS co-ordinate?

# Resources

* [planning-extract](https://github.com/i-dot-ai/planning-extract/) — our work with [i.AI](https://ai.gov.uk/) on [extracting data from documents](https://github.com/digital-land/digital-land/issues/360)
* [Data quality needs](https://digital-land.github.io/technical-documentation/data-operations-manual/Explanation/Key-Concepts/Data-quality-needs/) — notes on our data quality framework
* [specification](https://digital-land.github.io/specification/) — the planning data model
* [config](https://github.com/digital-land/config/) — source for our pipeline configuration
* [datasette](https://datasette.planning.data.gov.uk) — the output of our data pipeline
* [quality](https://datasette.planning.data.gov.uk/digital-land/quality) — categories for scoring the quality of an entity, dataset and provision


# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and data in this repository is
[© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/)
and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) licence.
