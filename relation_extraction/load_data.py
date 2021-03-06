import os
import sys
import collections
import itertools
import math
import random
import numpy as np
import tensorflow as tf

from six.moves import xrange  # pylint: disable=redefined-builtin
from lxml import etree

from structures.sentence_structure import Sentence, Token, Dependency
from structures.instances import Instance


def build_dataset(words, occur_count = None):
    """Process raw inputs into a dataset."""
    num_total_words = len(set(words))
    discard_count = 0
    if occur_count is not None:
        for c in collections.Counter(words):
            if collections.Counter(words)[c] < occur_count:
                discard_count +=1

    num_words = num_total_words - discard_count

    count = []
    count.extend(collections.Counter(words).most_common(num_words))
    dictionary = dict()
    for word, _ in count:
        dictionary[word] = len(dictionary)
    data = list()
    for word in words:
        if word in dictionary:
            index = dictionary[word]
            data.append(index)
    reversed_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
    return data, count, dictionary, reversed_dictionary


def build_instances_training(candidate_sentences, distant_interactions, entity_1_list = None, entity_2_list = None, symmetric = False):
    path_word_vocabulary = []
    words_between_entities_vocabulary = []
    dep_type_vocabulary = []
    candidate_instances = []
    for candidate_sentence in candidate_sentences:
        entity_pairs = candidate_sentence.get_entity_pairs()

        for pair in entity_pairs:
            entity_1_token = candidate_sentence.get_token(pair[0])
            entity_2_token = candidate_sentence.get_token(pair[1])
            entity_1 = entity_1_token.get_normalized_ner().split('|')
            entity_2 = entity_2_token.get_normalized_ner().split('|')

            if entity_1_list is not None:
                if len(set(entity_1).intersection(entity_1_list)) == 0:
                    continue

                # check if entity_2 overlaps with entity_1_list if so continue
                if len(set(entity_2).intersection(entity_1_list)) > 0:
                    continue

            if entity_2_list is not None:
                if len(set(entity_2).intersection(entity_2_list)) == 0:
                    continue

                # check if entity_1 overlaps with entity_2_list if so continue
                if len(set(entity_1).intersection(entity_2_list)) > 0:
                    continue

            entity_combos = set(itertools.product(entity_1,entity_2))

            if len(entity_combos.intersection(distant_interactions)) > 0:
                candidate_instance = Instance(candidate_sentence, pair[0], pair[1], 1)
                candidate_instances.append(candidate_instance)

                path_word_vocabulary += candidate_instance.get_dep_word_path()
                words_between_entities_vocabulary += candidate_instance.get_between_words()

                if symmetric == False:
                    dep_type_vocabulary.append(' '.join(candidate_instance.get_type_dependency_path()))
                else:
                    dep_type_vocabulary_set = set(dep_type_vocabulary)
                    forward_dep_type_path = ' '.join(candidate_instance.get_type_dependency_path())
                    reverse_dep_type_path = ' '.join(candidate_instance.get_reverse_type_dependency_path())
                    if forward_dep_type_path in dep_type_vocabulary_set and reverse_dep_type_path not in dep_type_vocabulary_set:
                        dep_type_vocabulary.append(forward_dep_type_path)
                    elif forward_dep_type_path not in dep_type_vocabulary_set and reverse_dep_type_path in dep_type_vocabulary_set:
                        dep_type_vocabulary.append(reverse_dep_type_path)
                    elif forward_dep_type_path not in dep_type_vocabulary_set and reverse_dep_type_path not in dep_type_vocabulary_set:
                        dep_type_vocabulary.append(forward_dep_type_path)
                    elif forward_dep_type_path in dep_type_vocabulary_set and reverse_dep_type_path in dep_type_vocabulary_set:
                        dep_type_vocabulary.append(forward_dep_type_path)


            else:
                candidate_instance = Instance(candidate_sentence, pair[0], pair[1], 0)
                candidate_instances.append(candidate_instance)

    data, count, dictionary, reversed_dictionary = build_dataset(path_word_vocabulary)
    dep_data, dep_count, dep_dictionary, dep_reversed_dictionary = build_dataset(dep_type_vocabulary)
    between_data, between_count, between_dictionary, between_reversed_dictionary = build_dataset(words_between_entities_vocabulary)
    common_words_file = open('./static_data/common_words.txt','rU')
    lines = common_words_file.readlines()
    common_words_file.close()

    common_words = set()
    for l in lines:
        common_words.add(l.split()[0])

    dep_path_word_dictionary = {}
    array_place = 0
    for c in count:
        if c[0] not in common_words:
            dep_path_word_dictionary[c[0]] = array_place
            array_place += 1

    between_word_dictionary = {}
    array_place = 0
    for c in between_count:
        if c[0] not in common_words:
            between_word_dictionary[c[0]] = array_place
            array_place += 1

    print(dep_dictionary)
    print(dep_path_word_dictionary)
    print(between_word_dictionary)

    for ci in candidate_instances:
        ci.build_features(dep_dictionary, dep_path_word_dictionary, between_word_dictionary, symmetric)


    return candidate_instances, dep_dictionary, dep_path_word_dictionary, between_word_dictionary

def build_instances_testing(test_sentences, dep_dictionary, dep_path_word_dictionary, between_word_dictionary, distant_interactions, entity_1_list =  None, entity_2_list = None, symmetric = False):
    test_instances = []
    for test_sentence in test_sentences:
        entity_pairs = test_sentence.get_entity_pairs()

        for pair in entity_pairs:
            entity_1_token = test_sentence.get_token(pair[0])
            entity_2_token = test_sentence.get_token(pair[1])
            entity_1 = entity_1_token.get_normalized_ner().split('|')
            entity_2 = entity_2_token.get_normalized_ner().split('|')
            if entity_1_list is not None:
                if len(set(entity_1).intersection(entity_1_list)) == 0:
                    continue

                #check if entity_2 overlaps with entity_1_list if so continue
                if len(set(entity_2).intersection(entity_1_list)) > 0:
                    continue

            if entity_2_list is not None:
                if len(set(entity_2).intersection(entity_2_list)) == 0:
                    continue
                #check if entity_1 overlaps with entity_2_list if so continue
                if len(set(entity_1).intersection(entity_2_list)) > 0:
                   continue

            entity_combos = set(itertools.product(entity_1,entity_2))

            if len(entity_combos.intersection(distant_interactions)) > 0:
                candidate_instance = Instance(test_sentence, pair[0], pair[1], 1)
                test_instances.append(candidate_instance)
            else:
                candidate_instance = Instance(test_sentence, pair[0], pair[1], 0)
                test_instances.append(candidate_instance)


    for instance in test_instances:
        instance.build_features(dep_dictionary, dep_path_word_dictionary,  between_word_dictionary, symmetric)

    return test_instances

def build_instances_predict(predict_sentences, dep_dictionary, dep_path_word_dictionary, between_word_dictionary, entity_1_list = None, entity_2_list = None, symmetric = False):
    predict_instances = []
    for p_sentence in predict_sentences:
        entity_pairs = p_sentence.get_entity_pairs()

        for pair in entity_pairs:
            entity_1_token = p_sentence.get_token(pair[0])
            entity_2_token = p_sentence.get_token(pair[1])
            entity_1 = entity_1_token.get_normalized_ner().split('|')
            entity_2 = entity_2_token.get_normalized_ner().split('|')
            if entity_1_list is not None:
                if len(set(entity_1).intersection(entity_1_list)) == 0:
                    continue

                #check if entity_2 overlaps with entity_1_list if so continue
                if len(set(entity_2).intersection(entity_1_list)) > 0:
                    continue

            if entity_2_list is not None:
                if len(set(entity_2).intersection(entity_2_list)) == 0:
                    continue
                #check if entity_1 overlaps with entity_2_list if so continue
                if len(set(entity_1).intersection(entity_2_list)) > 0:
                   continue

            candidate_instance = Instance(p_sentence, pair[0], pair[1], -1)
            predict_instances.append(candidate_instance)

    for instance in predict_instances:
        instance.build_features(dep_dictionary, dep_path_word_dictionary,  between_word_dictionary, symmetric)

    return predict_instances

def load_xml(xml_file, entity_1, entity_2):
    tree = etree.parse(xml_file)
    root = tree.getroot()
    candidate_sentences = []
    sentences = list(root.iter('sentence'))


    for sentence in sentences:
        candidate_sentence = Sentence(sentence.get('id'))
        tokens = list(sentence.iter('token'))

        for token in tokens:
            normalized_ner = None
            ner = token.find('NER').text
            if token.find('NormalizedNER') is not None:
                normalized_ner = token.find('NormalizedNER').text

            candidate_token = Token(token.get('id'), token.find('word').text, token.find('lemma').text, token.find('CharacterOffsetBegin').text,
                                    token.find('CharacterOffsetEnd').text, token.find('POS').text, ner, normalized_ner)
            candidate_sentence.add_token(candidate_token)

        dependencies = list(sentence.iter('dependencies'))
        basic_dependencies = dependencies[0]
        deps = list(basic_dependencies.iter('dep'))
        for d in deps:
            candidate_dep = Dependency(d.get('type'), candidate_sentence.get_token(d.find('governor').get('idx')), candidate_sentence.get_token(d.find('dependent').get('idx')))
            candidate_sentence.add_dependency(candidate_dep)

        candidate_sentence.generate_entity_pairs(entity_1, entity_2)
        candidate_sentence.build_dependency_matrix()
        candidate_sentences.append(candidate_sentence)

    return candidate_sentences


def load_distant_kb(distant_kb_file, column_a, column_b):
    distant_interactions = set()
    file = open(distant_kb_file,'rU')
    lines = file.readlines()
    file.close()

    for l in lines:
        split_line = l.split('\t')
        tuple = (split_line[column_a],split_line[column_b])
        distant_interactions.add(tuple)

    return distant_interactions

def load_id_list(id_list,column_a):
    id_set = set()
    file = open(id_list,'rU')
    lines = file.readlines()
    file.close()

    for l in lines:
        split_line = l.split('\t')
        id_set.add(split_line[column_a])

    return id_set
