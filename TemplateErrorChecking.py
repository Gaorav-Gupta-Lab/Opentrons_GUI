
"""
Dennis A Simpson
University of North Carolina at Chapel Hill
450 West Drive
Chapel Hill, NC  27599

@Copyright 2021
"""

import sys
from distutils import log
from collections import defaultdict
from types import SimpleNamespace
import csv
import Tool_Box
from Utilities import parse_sample_template, calculate_volumes

__version__ = "0.10.0"


class TemplateErrorChecking:
    def __init__(self, input_file):
        self.stdout = sys.stdout
        self.sample_dictionary, self.args = parse_sample_template(input_file)
        self.pipette_info_dict = {"p10_multi": "opentrons_96_tiprack_10ul",
                                  "p10_single": "opentrons_96_tiprack_10ul",
                                  "p20_single_gen2": ["opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul"],
                                  "p300_single_gen2": ["opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_300ul"]
                                  }
        self.slot_dict = None
        self.left_tip_boxes = []
        self.right_tip_boxes = []
        self.max_template_vol = None
        self.well_label_dict = self.well_labels()

    @staticmethod
    def parse_sample_file(input_file):
        """
        Parse TSV file
        :param input_file:
        :return:
        """
        line_num = 0
        options_dictionary = defaultdict(str)
        sample_dictionary = defaultdict(list)
        index_file = list(csv.reader(open(input_file), delimiter='\t'))

        for line in index_file:
            # Get the program linked to the template file.  Data should always be the first cell of line one.
            if line_num == 0:
                options_dictionary["Program"] = line[0]

            line_num += 1
            col_count = len(line)
            tmp_line = []
            sample_key = ""
            if col_count > 0 and "#" not in line[0] and len(line[0].split("#")[0]) > 0:
                # Skip any lines that are blank or comments.

                for i in range(7):
                    try:
                        line[i] = line[i].split("#")[0]  # Strip out end of line comments and white space.
                    except IndexError:
                        continue

                    if i == 0 and "--" in line[0]:
                        key = line[0].strip('--')
                        key_value = line[1]
                        if "Target_" in key or "PositiveControl_" in key:
                            key_value = (line[1], line[2], line[3])
                        options_dictionary[key] = key_value
                    elif "--" not in line[0] and int(line[0]) < 12:
                        sample_key = line[0], line[1]
                        tmp_line.append(line[i])
                if sample_key:
                    sample_dictionary[sample_key] = tmp_line

        return sample_dictionary, SimpleNamespace(**options_dictionary)

    def slot_error_check(self):
        slot_error = ""
        slot_list = \
            ["Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "Slot6", "Slot7", "Slot8", "Slot9", "Slot10", "Slot11"]

        slot_dict = {}
        print("Checking Labware Definitions in Slots")

        for i in range(len(slot_list)):
            labware = getattr(self.args, "{}".format(slot_list[i]))

            if labware and labware not in self.labware_slot_definitions:
                msg = "ERROR: Slot {} labware definition not in dictionary.\nCheck spelling.".format(slot_list[i])
                slot_error = msg
            slot_dict[str(i + 1)] = labware

        if slot_error:
            print("NOTICE: There are errors in the labware definitions.  Correct these and run again\n")
        else:
            print("\tLabware definitions in slots passed")

        self.slot_dict = slot_dict

        return slot_error

    def pipette_error_check(self):
        msg = ""
        pipette_error = False
        log.info("Checking Pipette Definitions")
        if self.args.LeftPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.LeftPipette, "Left Pipette")
        if self.args.RightPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.RightPipette, "Right Pipette")
        if pipette_error:
            msg = "There is an error in the one of the pipette definitions"
            print("ERROR: {}".format(msg))
        else:
            print("\tPipette definitions passed.")

        return msg

    def tip_box_error_check(self):
        print("Checking Pipette Tip Box Definitions")
        msg = ""
        for slot in self.slot_dict:
            labware = self.slot_dict[slot]
            lft_pipette_labware = self.pipette_info_dict[self.args.LeftPipette]
            rt_pipette_labware = self.pipette_info_dict[self.args.RightPipette]
            if labware in lft_pipette_labware:
                self.left_tip_boxes.append(slot)
            elif labware in rt_pipette_labware:
                self.right_tip_boxes.append(slot)

        if len(self.left_tip_boxes) == 0 == len(self.right_tip_boxes):
            print("ERROR:  No pipette tip boxes defined.")
            msg = "ERROR:  No pipette tip boxes defined."

        else:
            print("\tPipette tip box definitions passed")

        return msg

    def slot_usage_error_check(self, labware, type_check):
        msg = ""
        # Check the reagent slot and reagent wells
        if not self.args.ReagentSlot:
            msg = '{} Slot definition missing.'.format(type_check)
            print("ERROR: {}".format(msg))
        else:
            for pipette in self.pipette_info_dict:
                if labware in self.pipette_info_dict[pipette]:
                    msg = "{} slot contains a pipette tip box".format(type_check)
                    print("ERROR: {}".format(msg))

        return msg

    def dispense_samples(self, sample_data_dict, water_aspirated, p20_tips_used, p300_tips_used):
        """
        @param sample_data_dict:
        @param water_aspirated:
        """

        sample_parameters = self.sample_dictionary

        for sample_key in sample_parameters:
            sample_dest_wells = sample_data_dict[sample_key][3]
            sample_vol = sample_data_dict[sample_key][0]
            diluent_vol = sample_data_dict[sample_key][1]
            diluted_sample_vol = sample_data_dict[sample_key][2]

            # If no dilution is necessary, dispense sample and continue
            if diluted_sample_vol == 0:
                if sample_vol <= 20:
                    p20_tips_used += 1
                else:
                    p300_tips_used += 1
                continue

            # Adjust volume of diluted sample to make sure there is enough
            diluted_template_needed = diluted_sample_vol * (len(sample_dest_wells) + 1)
            diluted_template_on_hand = sample_vol + diluent_vol
            diluted_template_factor = 1.0
            if diluted_template_needed <= diluted_template_on_hand:
                diluted_template_factor = diluted_template_needed / diluted_template_on_hand
                if diluted_template_factor <= 1.5 and (sample_vol * diluted_template_factor) < 10:
                    diluted_template_factor = 2.0

            diluent_vol = diluent_vol * diluted_template_factor
            if diluted_sample_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            if (sample_vol*diluted_template_factor) <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            if diluent_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            water_aspirated += diluent_vol
        return water_aspirated, p20_tips_used, p300_tips_used

    def droplet_pcr(self):
        """

        :rtype: object
        """
        reagent_slot = self.args.ReagentSlot
        reagent_labware = self.slot_dict[reagent_slot]

        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")
        if msg:
            return msg

        target_count = 0
        for i in range(10):
            target = getattr(self.args, "Target_{}".format(i+1))
            if target:
                target_count += 1

        sample_data_dict, water_well_dict, target_well_dict, used_wells, layout_data, msg = \
            self.ddpcr_sample_processing()

        if msg:
            return msg

        p20_tips_used = 0
        p300_tips_used = 0
        water_aspirated = 0

        for well in water_well_dict:
            water_vol = water_well_dict[well]
            if water_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1
            water_aspirated += water_vol

        for target in target_well_dict:
            reagent_used = float(self.args.ReagentVolume) * 2
            target_well_count = 0
            target_info = getattr(self.args, "Target_{}".format(target))
            reagent_name = target_info[1]
            reagent_well_vol = float(target_info[2])
            reagent_aspirated = float(self.args.ReagentVolume)

            target_well_list = target_well_dict[target]
            for well in target_well_list:
                reagent_used += reagent_aspirated
                if reagent_aspirated <= 20:
                    p20_tips_used += 1
                else:
                    p300_tips_used += 1

            # Add a reagent tip for the no template control
            if reagent_aspirated <= 20:
                p20_tips_used += 2
            else:
                p300_tips_used += 2

            target_well_count += len(target_well_list)+2
            if reagent_used >= reagent_well_vol:
                msg = "Program requires minimum of {} uL {}.  You have {} uL."\
                      .format(reagent_used, reagent_name, reagent_well_vol)
                return msg

        water_aspirated, p20_tips_used, p300_tips_used = \
            self.dispense_samples(sample_data_dict, water_aspirated, p20_tips_used, p300_tips_used)
        water_aspirated, p20_tips_used, p300_tips_used = \
            self.empty_well_vol(self.plate_layout(), target_well_count, p20_tips_used, p300_tips_used, water_aspirated)

        # Check Water Volume
        if int(self.args.WaterResVol) <= water_aspirated:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(water_aspirated, self.args.WaterResVol)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(p20_tips_used, p300_tips_used)
        if msg:
            return msg

    def generic_pcr(self):
        """
        Perform error checking on the template for the Generic PCR program.
        :return:
        """

        reagent_slot = self.args.ReagentSlot
        reagent_labware = self.slot_dict[reagent_slot]
        self.max_template_vol = float(self.args.PCR_Volume)*0.5
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")
        if msg:
            return msg

        try:
            water_control_slot = self.args.WaterControl.split(",")[0]
            water_control_labware = self.slot_dict[water_control_slot]
            water_control_well = self.args.WaterControl.split(",")[1]
        except IndexError:
            return "--WaterControl value not formatted correctly in TSV file"

        msg = self.slot_usage_error_check(water_control_labware, type_check="--WaterControl")
        if msg:
            return msg

        reagent_labware_pass = False

        for key in self.well_label_dict:
            if key == water_control_labware:
                label_list = self.well_label_dict[key]
                if water_control_well not in label_list:
                    msg = "The well defined for the Water Control Sample is not possible for {}"\
                        .format(water_control_labware)
                    print("ERROR: {}".format(msg))
                    return msg

            if key in reagent_labware:
                reagent_labware_pass = True
                label_list = self.well_label_dict[key]
                if self.args.WaterWell not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

                if self.args.PCR_MixWell not in label_list:
                    msg = "The well defined for the PCR Mix is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        if not reagent_labware_pass:
            print("ERROR: The Reagent labware is not correctly defined.")

        # Process Sample data;
        source_test = []
        dest_test = []
        for sample_key in self.sample_dictionary:
            sample_source_slot = self.sample_dictionary[sample_key][0]
            sample_source_labware = self.slot_dict[sample_source_slot]
            sample_source_well = self.sample_dictionary[sample_key][1]
            sample_name = self.sample_dictionary[sample_key][2]
            sample_dest_slot = self.sample_dictionary[sample_key][4]
            sample_dest_labware = self.slot_dict[sample_dest_slot]
            sample_dest_well = self.sample_dictionary[sample_key][5].split(",")
            source_test.append("{}+{}".format(sample_source_slot, sample_source_well))

            # Make sure the sample source and destination slots are not tip boxes.
            msg = self.slot_usage_error_check(sample_source_labware, type_check=sample_name)
            if msg:
                return msg
            msg = self.slot_usage_error_check(sample_dest_labware, type_check="{} DESTINATION".format(sample_name))
            if msg:
                return msg

            # If there are replicates a single sample can have more than one destination well.
            for well in sample_dest_well:
                dest_test.append("{}+{}".format(sample_dest_slot, well))

        for source in source_test:
            if source in dest_test:
                msg = "More than one sample share the same source and/or destinations"
                print("ERROR:  {}".format(msg))
                return msg

        wells_used = len(dest_test)+1
        water_required, left_tips_used, right_tips_used, msg = self.pcr_sample_processing(wells_used)

        # Sample too dilute error
        if msg:
            return msg

        # Check Water Volume
        if float(self.args.WaterResVol) <= water_required:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(int(water_required), self.args.WaterResVol)
            return msg

        # Check PCR reagent volume
        pcr_mix_required = float(self.args.PCR_Volume)*0.5*wells_used
        if pcr_mix_required > float(self.args.PCR_MixResVolume):
            msg = "Program requires {} uL of PCR mix.  You have {} uL"\
                .format(pcr_mix_required, self.args.PCR_MixResVolume)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(left_tips_used, right_tips_used)
        if msg:
            return msg

    def available_tips(self, left_tips_used, right_tips_used):
        tip_box_layout = self.plate_layout()
        left_available = \
            (len(self.left_tip_boxes)*96)-tip_box_layout.index(self.args.LeftPipetteFirstTip)
        right_available = \
            (len(self.right_tip_boxes)*96)-tip_box_layout.index(self.args.RightPipetteFirstTip)

        if self.args.LeftPipette == "p20_single_gen2":
            if left_available < 0:
                left_available = 0
            if left_available < left_tips_used:
                msg = "Program requires {}, {} tips.  {} tips provided."\
                    .format(int(left_tips_used), self.args.LeftPipette, left_available)
                return msg

        if self.args.RightPipette == "p300_single_gen2":
            if right_available < 0:
                right_available = 0
            if right_available < right_tips_used:
                msg = "Program requires {}, {} tips.  {} tips provided"\
                    .format(int(right_tips_used), self.args.RightPipette, right_available)
                return msg

    def illumina_dual_indexing(self):

        reagent_slot = self.args.ReagentSlot
        reagent_labware = self.slot_dict[reagent_slot]

        # Check for slot conflicts
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")
        if msg:
            return msg
        msg = self.slot_usage_error_check(self.slot_dict[self.args.IndexPrimersSlot], type_check="Index Primers")
        if msg:
            return msg

        self.max_template_vol = float(self.args.PCR_Volume) * 0.5

        for key in self.well_label_dict:
            label_list = self.well_label_dict[key]
            if key in reagent_labware:
                if self.args.WaterWell not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

                if self.args.PCR_MixWell not in label_list:
                    msg = "The well defined for the PCR Mix is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        # Process Sample data;
        source_test = []
        dest_test = []
        index_dict = {}
        for sample_key in self.sample_dictionary:
            sample_source_slot = self.sample_dictionary[sample_key][0]
            sample_source_well = self.sample_dictionary[sample_key][1]
            sample_index = self.sample_dictionary[sample_key][2]
            sample_name = self.sample_dictionary[sample_key][3]
            sample_dest_slot = self.sample_dictionary[sample_key][5]
            sample_dest_well = self.sample_dictionary[sample_key][6]
            source_test.append("{}+{}".format(sample_source_slot, sample_source_well))
            # Make sure the sample source and destination slots are not tip boxes.
            msg = self.slot_usage_error_check(self.slot_dict[sample_source_slot], type_check=sample_name)
            if msg:
                return msg

            msg = self.slot_usage_error_check(self.slot_dict[sample_dest_slot], type_check="{} DESTINATION"
                                              .format(sample_name))
            if msg:
                return msg

            if sample_index in index_dict:
                msg = "Sample index {} used for samples {} and {}"\
                    .format(sample_index, index_dict[sample_index], sample_name)
                return msg
            else:
                index_dict[sample_index] = sample_name


        dest_test.append("{}+{}".format(sample_dest_slot, sample_dest_well))
        for source in source_test:
            if source in dest_test:
                msg = "More than one sample share the same source and/or destinations"
                print("ERROR:  {}".format(msg))
                return msg
        Tool_Box.debug_messenger(dest_test)
        wells_used = len(dest_test)
        water_required, left_tips_used, right_tips_used, msg = self.pcr_sample_processing(wells_used, indexing_rxn=True)

        # This is our warning of samples being too dilute.
        if msg:
            return msg

        # Check Water Volume
        if float(self.args.WaterResVol) < water_required:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(water_required, self.args.WaterResVol)
            return msg

        # Check PCR reagent volume
        pcr_mix_required = float(self.args.PCR_Volume)*0.5*wells_used

        if pcr_mix_required > float(self.args.PCR_MixResVolume):
            msg = "Program requires {} uL of PCR mix.  You have {} uL"\
                .format(pcr_mix_required, self.args.PCR_MixResVolume)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(left_tips_used, right_tips_used)
        if msg:
            return msg

    @property
    def labware_slot_definitions(self):
        """
        Labware that we have on-hand.
        :return:
        """
        labware_list = [
            "vwrmicrocentrifugetube1.5ml_24_tuberack_1500ul", "stacked_96_well", "8_well_strip_tubes_200ul",
            "opentrons_96_tiprack_10ul", "opentrons_96_tiprack_20ul", "opentrons_96_tiprack_300ul",
            "vwrscrewcapcentrifugetube5ml_15_tuberack_5000ul", "screwcap_24_tuberack_500ul",
            "opentrons_24_tuberack_generic_2ml_screwcap", "opentrons_96_filtertiprack_20ul",
            "opentrons_96_filtertiprack_20ul"]

        return labware_list

    def well_labels(self):
        """
        Create a dictionary of well labels for each loaded labware.
        :return:
        """

        def well_list(row_count, column_count):
            row_labels = \
                ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                 "U", "V", "W", "X", "Y", "Z"]

            temp_list = []
            for r in range(row_count):
                for i in range(column_count):
                    temp_list.append("{}{}".format(row_labels[r], i + 1))

            return temp_list

        well_labels_dict = defaultdict(list)
        for labware in self.labware_slot_definitions:
            w96 = well_list(8, 12)
            w24 = well_list(4, 6)
            w15 = well_list(3, 5)

            if "24" in labware:
                well_labels_dict[labware] = w24
            elif "96" in labware:
                well_labels_dict[labware] = w96
            elif "_15_tuberack" in labware:
                well_labels_dict[labware] = w15
            elif len(well_labels_dict) == 0:
                msg = "Well label definitions failed.  Incorrect labware passed.  Template file is bad"
                print("ERROR:  {}".format(msg))
                return msg

        return well_labels_dict

    def pipette_definition_error_check(self, error_state, pipette, pipette_str):
        if pipette not in self.pipette_info_dict:
            error_state = True
            print("ERROR:  {} definition not correct".format(pipette_str))
        return error_state

    @staticmethod
    def plate_layout():
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        plate_layout_by_column = []
        for i in range(12):
            for row in rows:
                plate_layout_by_column.append("{}{}".format(row, i + 1))
        return plate_layout_by_column

    def pcr_sample_processing(self, used_wells, indexing_rxn=False):
        sample_parameters = self.sample_dictionary
        pcr_mix_required = float(self.args.PCR_Volume) * 0.5
        indexing_tips = 0
        if indexing_rxn:
            indexing_tips = used_wells*2

        left_tips_used = 4
        right_tips_used = 4
        if self.args.LeftPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            left_tips_used = used_wells+indexing_tips
        elif self.args.LeftPipette == "p300_single_gen2" and pcr_mix_required > 20:
            left_tips_used = used_wells

        if self.args.RightPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            right_tips_used = used_wells+indexing_tips
        elif self.args.RightPipette == "p300_single_gen2" and pcr_mix_required > 20:
            right_tips_used = used_wells

        template_required = float(self.args.DNA_in_Reaction)
        water_required = 0
        msg = ""
        for sample_key in sample_parameters:
            if indexing_rxn:
                sample_concentration = float(sample_parameters[sample_key][4])
            else:
                sample_concentration = float(sample_parameters[sample_key][3])
            sample_vol = round(template_required/sample_concentration, 2)
            water_vol = (float(self.args.PCR_Volume)*0.5)-sample_vol
            if sample_vol > float(self.args.PCR_Volume)*0.5:
                print(template_required, sample_vol, sample_concentration)
                msg = "Sample {} is too dilute.  Minimum required concentration is {} ng/uL."\
                    .format(sample_parameters[sample_key][2],
                            round(template_required/(float(self.args.PCR_Volume)*0.5), 2))
                return 0, 0, 0, msg
            water_required += water_vol
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, water_vol)
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, sample_vol)

        return round(water_required, 1), left_tips_used, int(right_tips_used), msg

    def tip_counter(self, left_tips_used, right_tips_used, volume):
        if self.args.LeftPipette == "p20_single_gen2" and volume <= 20:
            left_tips_used += 1
        elif self.args.LeftPipette == "p300_single_gen2" and volume > 20:
            left_tips_used += 1

        if self.args.RightPipette == "p20_single_gen2" and volume <= 20:
            right_tips_used += 1
        elif self.args.RightPipette == "p300_single_gen2" and volume > 20:
            right_tips_used += 1

        return left_tips_used, right_tips_used

    def ddpcr_sample_processing(self):
        """

        :rtype: int
        """

        # Check if destination PCR plate and dilution labware are tip boxes
        msg = self.slot_usage_error_check(self.slot_dict[self.args.PCR_PlateSlot], type_check="PCR Plate")
        if msg:
            return "", "", "", "", "", msg
        msg = \
            self.slot_usage_error_check(self.slot_dict[self.args.DilutionPlateSlot], type_check="Dilution Labware")
        if msg:
            return "", "", "", "", "", msg

        sample_parameters = self.sample_dictionary
        rxn_vol = float(self.args.PCR_Volume)

        self.max_template_vol = round(rxn_vol-float(self.args.ReagentVolume), 2)

        # There is a single no template control for every target that uses max volume.
        plate_layout_by_column = self.plate_layout()
        sample_data_dict = defaultdict(list)
        target_well_dict = defaultdict(list)
        water_well_dict = defaultdict(float)
        layout_data = defaultdict(list)

        # Builds the data frame for printing the plate layout file
        for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            layout_data[k] = ['', '', '', '', '', '', '', '', '', '', '', '', ]

        used_wells = []
        dest_well_count = 0
        template_in_rxn = float(self.args.DNA_in_Reaction)
        for sample_key in sample_parameters:
            sample_concentration = float(sample_parameters[sample_key][3])
            targets = sample_parameters[sample_key][4].split(",")
            replicates = int(sample_parameters[sample_key][5])
            sample_name = sample_parameters[sample_key][2]

            if (template_in_rxn/sample_concentration) > self.max_template_vol:
                min_sample_conc = round(template_in_rxn/self.max_template_vol, 2)
                msg = "Sample '{}' too dilute.\nMinimum sample concentration required is {} ng/uL"\
                    .format(sample_name, min_sample_conc)

                return "", "", "", "", "", msg

            sample_vol, diluent_vol, diluted_sample_vol, reaction_water_vol, max_template_vol = \
                calculate_volumes(self.args, sample_concentration)

            sample_wells = []
            for target in targets:
                for i in range(replicates):
                    well = plate_layout_by_column[dest_well_count]
                    water_well_dict[well] = reaction_water_vol
                    target_well_dict[target].append(well)
                    sample_wells.append(well)
                    used_wells.append(well)
                    dest_well_count += 1

            sample_data_dict[sample_key] = [sample_vol, diluent_vol, diluted_sample_vol, sample_wells]

        # Define our positive control wells for the targets.
        for target in target_well_dict:
            well = plate_layout_by_column[dest_well_count]
            used_wells.append(well)
            water_well_dict[well] = self.max_template_vol
            dest_well_count += 1

        return sample_data_dict, water_well_dict, target_well_dict, used_wells, layout_data, ""

    def empty_well_vol(self, plate_template, used_well_count, p20_tip_count, p300_tip_count, total_water):
        """
        This will determine the amount of water and number of tips required to fill the remaining empty wells in a
        column.
        @rtype: object
        """

        last_used_well = plate_template[used_well_count-1]
        row = last_used_well[0]
        column = int(last_used_well.split(row)[1])
        wells_remaining = 12 - column
        total_water += wells_remaining*float(self.args.PCR_Volume)
        p20_tip_count, p300_tip_count = self.tip_counter(p20_tip_count, p300_tip_count, float(self.args.PCR_Volume))

        return total_water, p20_tip_count, p300_tip_count

    def calculate_volumes(self, sample_concentration):
        """
        Calculates volumes for dilution and distribution of sample.
        Returns a list of tuples consisting of
        (uL of sample to dilute, uL of water for dilution), (uL of diluted sample in reaction, uL of water in reaction)
        @param args:
        @param sample_concentration:
        @return:
        """

        template_in_reaction = float(self.args.DNA_in_Reaction)
        # Target Concentration is used to keep volumes > 1 uL
        target_concentration = template_in_reaction / 2

        """
        # There is the potential to need the max template volume for the lower dilutions.  This defines those.
        # Not needed.  Simply make extra volume based on number of replicates.
        dilution_template = [(4, 4), (2, 6), (2, 10), (1, 7), (1, 9), (1, 11)]
        if args.PCR_MixConcentration == "4x":
            dilution_template = [(7, 7), (4, 12), (3, 15), (2, 14), (2, 18), (2, 22)]
        """
        min_dna_in_reaction = template_in_reaction / self.max_template_vol

        # If template concentration per uL is less than desired template in reaction then no dilution is necessary.
        if sample_concentration <= target_concentration:
            sample_vol = template_in_reaction / sample_concentration
            return sample_vol, 0, round(self.max_template_vol - sample_vol, 2), self.max_template_vol

        # This will test a series of dilutions up to a 1:200.
        for i in range(50):
            dilution = (i + 1) * 2
            diluted_dna_conc = sample_concentration / dilution

            if target_concentration >= diluted_dna_conc >= min_dna_in_reaction:
                dilution_data = (1, dilution - 1)
                diluted_sample_vol = round(template_in_reaction / diluted_dna_conc, 2)
                reaction_water_vol = self.max_template_vol - diluted_sample_vol

                return dilution_data[0], dilution_data[1], diluted_sample_vol, reaction_water_vol
