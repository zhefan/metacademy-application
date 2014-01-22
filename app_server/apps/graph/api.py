import pdb
import string
import random

# myapp/api.py
from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization # TODO change

from apps.graph.models import Concept, Edge, Flag, Graph, ConceptResource
from apps.graph.serializers import ConceptSerializer, GraphSerializer


class FlagResource(ModelResource):
    class Meta:
        fields = ("text",)
        include_resource_uri = False
        queryset = Flag.objects.all()
        resource_name = 'flag'
        authorization = Authorization()

class ShellConceptResource(ModelResource):
    class Meta:
        fields = ("id", "tag")
        queryset = Concept.objects.all()
        resource_name = 'concept'
        include_resource_uri = False
        authorization = Authorization()

class EdgeResource(ModelResource):
    source = fields.ForeignKey(ShellConceptResource, "source", full=True)
    target = fields.ForeignKey(ShellConceptResource, "target", full=True)
    class Meta:
        queryset = Edge.objects.all()
        resource_name = 'edge'
        include_resource_uri = False
        authorization = Authorization()

    def dehydrate(self, bundle):
        # TODO better way to rename?
        bundle.data["edge_id"] = bundle.data["id"]
        del bundle.data["id"]
        return bundle

class ConceptResourceResource(ModelResource):
    concept = fields.ForeignKey(ShellConceptResource, "concept", full=True)
    class Meta:
        queryset = ConceptResource.objects.all()
        resource_name = 'conceptresource'
        authorization = Authorization()

class ConceptResource(ModelResource):
    dependencies = fields.ToManyField(EdgeResource, 'edge_target', full=True)
    resources = fields.ToManyField(ConceptResourceResource, 'concept_resource', full = True)
    flags = fields.ManyToManyField(FlagResource, 'flags', full=True)

    class Meta:
        queryset = Concept.objects.all()
        resource_name = 'concept'
        authorization = Authorization()
        serializer = GraphSerializer()

    def hydrate_id(self, bundle, **kwargs):
        # TODO need to normalize client side to better agree with server representation
        # FIXME after migrating to concept-storing database
        in_concept = bundle.data
        if in_concept.has_key("sid") and len(in_concept["sid"]):
            useid = in_concept["sid"]
            usetag = in_concept["id"]
        else:
            useid = in_concept["id"]
            usetag = in_concept["id"]
        in_concept["id"] = useid
        in_concept["tag"] = usetag

        return bundle

    def hydrate_flags(self, bundle):
        in_concept = bundle.data
        if in_concept["flags"]:
            flag_arr = []
            for flag in in_concept["flags"]:
                flag_arr.append({"text": flag})
            in_concept["flags"] = flag_arr
        return bundle

    def hydrate_dependencies(self, bundle):
        in_concept = bundle.data
        for i, in_inlink in enumerate(in_concept["dependencies"]):
            if type(in_inlink) != dict:
                # hack because hydrate can be called twice (https://github.com/toastdriven/django-tastypie/issues/390)
                continue

            inlink = {}

            inlink['source'] = {"id": in_inlink['sid_source'], "tag": in_inlink['source']}
            inlink['target'] = {"id": in_inlink['sid_target'], "tag": in_concept["tag"]}
            inlink['reason'] = in_inlink['reason']
            if not in_inlink.has_key("id"):
                inlink["id"] = in_inlink["sid_source"] + in_inlink["sid_target"]
            else:
                inlink["id"] = in_inlink["id"]
                in_concept["dependencies"][i] = inlink
        return bundle

    def hydrate_resources(self, bundle, **kwargs):
        """
        prep the resource data
        (can't do in ConceptResourceResouce hydrate because we need the tag/id
        from the concept)
        """

        for resource in bundle.data["resources"]:
            if type(resource) != dict:
                # hack because hydrate can be called twice (https://github.com/toastdriven/django-tastypie/issues/390)
                continue
            if resource.has_key("year"):
                try:
                    # must access bundle "longhand"
                    resource["year"]  = int(resource["year"])
                except:
                    resource["year"]  = None
            # FIXME this shouldn't exist here, or at least, it should check
            # that the id doesn't exist (for that 1 in 4.7x10^18 chance)
            if not resource.has_key("id"):
                resource["id"] = ''.join([random.choice(string.lowercase + string.digits) for i in range(12)])
            resource["concept"] = {"id": bundle.data["id"], "tag": bundle.data["tag"]}
            resource["additional_dependencies"] = resource["dependencies"]
            del resource["dependencies"]

        return bundle

class GraphResource(ModelResource):
    concepts = fields.ManyToManyField(ConceptResource, 'concepts', full=True)
    def alter_deserialized_list_data(self, request, data):
        pdb.set_trace()
    class Meta:
        queryset = Graph.objects.all()
        resource_name = 'graph'
        authorization = Authorization()
        serializer = GraphSerializer()