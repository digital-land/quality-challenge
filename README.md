# AI and machine learning challenges for improving planning data quality

This repository contains scenarios, test cases and code for challenges to scale how we improve the quality of data on https://planning.data.gov.uk

Testing and assuring our data quality is intended to complement our with work with [i.AI](https://ai.gov.uk/) to increase the availability of data by [extracting data from documents](https://github.com/digital-land/digital-land/issues/360). 

We expect to incorporate issues identified by these tests into the feedback we give to [data providers](https://submit.planning.data.gov.uk/), to help them improve the availability and quality of their planning data.

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

## Finding links to data sources

LPAs are also expected provide their conservation areas as data, following our [guidance](https://www.planning.data.gov.uk/guidance/specifications/conservation-area).

Our [endpoint](https://digital-land.github.io/specification/dataset/endpoint/) configuration contains an `endpoint-url` 
which we check and collect the data. Each night the platform makes a request from each endpoint, 
the [log](https://datasette.planning.data.gov.uk/digital-land/log) contains a record of the request
and saves the data downloaded as a [resource](https://datasette.planning.data.gov.uk/digital-land/resource).

We expect the `endpoint-url` to be documented and linked to from a webpage which is recorded as `documentation-url` for the endpoint.
This may be the same webpage as the information source page, but may also be a page on another domain. 
For example, [Barnet open data](https://open.barnet.gov.uk/dataset/20yo8/conservation-areas).

In this case we expect there to be a hyperlink from the information source page to the endpoint documentation page, 
and from the endpoint documentation page to the endpoint.

We also expect there to be a statement about the copyright and licensing of the data, which we currently record against the source.

* [provision](https://datasette.planning.data.gov.uk/digital-land/provision) contains the organisations expected to have information about each dataset.
* [organisation](https://datasette.planning.data.gov.uk/digital-land/organisation) dataset includes a link to each organisation's website.
* [source](https://datasette.planning.data.gov.uk/digital-land/source) contains existing source pages
* [endpoint](https://datasette.planning.data.gov.uk/digital-land/endpoint) contains existing endpoint pages, the URL where we download data from

*Our source and endpoint data is currently very messy. The source dataset contains placeholder entries with blank urls, and many of the documentation-urls are broken links, or point to endpoint webpages. We need to migrate to the source documentation-url linking to the information page, and the endpoint documentation-urls have been recorded against the source.*

We are adding datasets as we work through our backlog of [planning considerations](https://design.planning.data.gov.uk/planning-consideration/)
many of which are devolved to LPAs (currently [311 organisations](https://datasette.planning.data.gov.uk/digital-land/role_organisation?_sort=rowid&end_date__isblank=1&role__exact=local-planning-authority)). Finding sources for a new dataset on these LPA websites is timeconsuming. 

Once we have source and endpoint data, we need to monitor the LPA sites for changes, in particular publication of new endpoints,
and changes to licensing is a time-consuming and error-prone activity. 

## Comparing entities against information sources

## Finding and checking entity document links

## Finding duplicate entities

## Comparing boundaries to geographical features

## Finding and reconciling information from alternative sources

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
